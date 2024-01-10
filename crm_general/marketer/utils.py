def verified_marketer(product):
    n1, n2 = 0, 3

    images = product.images.first()
    if images:
        n1 += 1

    sizes = product.sizes.first()
    if sizes:
        n1 += 1

    if product.description:
        if len(product.description) > 100:
            n1 += 1

    return f'{n1}/{n2}'
