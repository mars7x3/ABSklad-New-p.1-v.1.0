from django.contrib import admin

from product.models import *

admin.site.register(Category)
admin.site.register(Collection)

admin.site.register(Review)
admin.site.register(ReviewImage)

admin.site.register(FilterMaxMin)
admin.site.register(ProductCostPrice)


class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    max_num = 1000
    extra = 0


class ProductCountInline(admin.TabularInline):
    model = ProductCount
    max_num = 1000
    extra = 0


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    max_num = 1000
    extra = 0


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    max_num = 1000
    extra = 0


class ProductCostPriceInline(admin.TabularInline):
    model = ProductCostPrice
    max_num = 1000
    extra = 0


@admin.register(AsiaProduct)
class AsiaProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductCountInline, ProductPriceInline, ProductSizeInline, ProductCostPriceInline]
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('id', 'title')
    list_display = ('id', 'title', 'vendor_code', 'category')
    list_display_links = ('id', 'title', 'vendor_code', 'category')
