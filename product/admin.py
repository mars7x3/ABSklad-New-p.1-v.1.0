from django.contrib import admin

from product.models import *

admin.site.register(AsiaProduct)
admin.site.register(Category)
admin.site.register(Collection)
admin.site.register(ProductPrice)
admin.site.register(ProductImage)
admin.site.register(ProductCount)
admin.site.register(ProductSize)

admin.site.register(Review)
admin.site.register(FilterMaxMin)

