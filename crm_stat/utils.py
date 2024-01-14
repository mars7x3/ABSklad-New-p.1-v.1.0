from typing import Iterable, Any, Callable

from django.db.models import Model, QuerySet
from django.utils import timezone


class Builder:
    def __init__(
        self,
        model,
        fields_map: dict[str, str],
        default_map: dict[str, Callable | str | int | float] = None
    ):
        assert issubclass(model, Model)
        self.model = model
        self.fields_map = fields_map
        self.default_map = default_map or {}

    def build_dict(self, item: dict, relations: dict[str | int, str | int] = None, ignore_fields: list[str] = None):
        collected_data = {}
        ignore_fields = ignore_fields or []

        for source, field in self.fields_map.items():
            if source in ignore_fields:
                continue

            if field not in item:
                continue

            value = item[field]

            if relations and value and source in relations:
                try:
                    value = relations[source][value]
                except KeyError as e:
                    print(source, " ", relations[source])
                    raise e
            collected_data[source] = value

        for source, value in self.default_map.items():
            if callable(value):
                value = value()
            collected_data[source] = value
        return collected_data

    def build_model_object(self, item: dict, relations: dict[str | int, str | int] = None):
        data = self.build_dict(item, relations=relations)
        if data:
            return self.model(**data)

    @staticmethod
    def _get_match_value(item, match_field: str | tuple[str]):
        if isinstance(match_field, str):
            return item[match_field]
        return tuple([item[field] for field in match_field])

    def build_model_by_list(
        self,
        items: Iterable[dict[str, Any]],
        match_field: str | tuple[str],
        from_keys: Iterable[str] = None,
        relations: dict[str, dict[str | int, str | int]] = None
    ):
        new = []
        processed = set()
        for data in items:
            item = [data[key] for key in from_keys] if from_keys else data
            if isinstance(item, dict):
                match_value = self._get_match_value(item, match_field)
                if match_value in processed:
                    continue

                instance = self.build_model_object(item, relations=relations)
                new.append(instance)
                processed.add(match_value)

            elif isinstance(item, list):
                for item_data in item:
                    match_value = self._get_match_value(item_data, match_field)
                    if match_value in processed:
                        continue

                    instance = self.build_model_object(item_data, relations=relations)
                    new.append(instance)
                    processed.add(match_value)
        return new


def stat_create_or_update(
    queryset: QuerySet,
    builder: Builder,
    match_field: str,
    match_field_y: str,
    update_ignore_fields: list[str],
    relations=None,
    on_create: Callable = None,
    on_update: Callable = None
) -> list[int | str]:
    if not queryset.exists():
        raise ValueError("Not found any objects!")

    another_model_match_field = builder.fields_map[match_field]
    match_filters = {match_field + "__in": queryset.values_list(match_field_y, flat=True)}
    saved_objs = {
        getattr(obj, match_field): obj
        for obj in builder.model.objects.filter(**match_filters)
    }
    saved_matches = list(saved_objs.keys())

    processed_objs = list()

    new_objs = queryset.exclude(pk__in=saved_matches)
    if new_objs.exists():
        if not on_create:
            items = new_objs.values(*builder.fields_map.values())
        else:
            items = on_create(new_objs)

        new_instances = builder.build_model_by_list(
            items=items,
            match_field=another_model_match_field,
            relations=relations
        )
        new_objs = builder.model.objects.bulk_create(new_instances)
        processed_objs.extend(new_objs)

    to_update_instances = queryset.filter(pk__in=saved_matches)

    if to_update_instances.exists():
        to_update = []

        if on_update:
            items = on_update(to_update_instances)
        else:
            items = to_update_instances.values(*builder.fields_map.values())

        update_fields = set()

        for data in items:
            update_instance = saved_objs[data[another_model_match_field]]

            update_data = builder.build_dict(data, ignore_fields=update_ignore_fields, relations=relations)
            for field, value in update_data.items():
                if hasattr(update_instance, field):
                    setattr(update_instance, field, value)
                    update_fields.add(field)

            if hasattr(update_instance, "updated_at"):
                update_instance.updated_at = timezone.now()
                update_fields.add("updated_at")

            to_update.append(update_instance)

        if to_update:
            builder.model.objects.bulk_update(to_update, fields=update_fields)
            processed_objs.extend(to_update)
    return processed_objs
