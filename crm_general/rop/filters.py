from crm_general.filters import ActiveFilterMixin, DateRangeFilterMixin, BaseFilter


class ManagerFilter(ActiveFilterMixin, DateRangeFilterMixin, BaseFilter):
    active_field = "user__is_active"
    start_date_field = "date_joined"
    end_date_field = "date_joined"
