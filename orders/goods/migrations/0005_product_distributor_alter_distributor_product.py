# Generated by Django 4.2.3 on 2023-08-12 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("goods", "0004_alter_product_options_product_price_with_delivery_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="distributor",
            field=models.ManyToManyField(
                related_name="products",
                through="goods.ProductDistributor",
                to="goods.distributor",
            ),
        ),
        migrations.AlterField(
            model_name="distributor",
            name="product",
            field=models.ManyToManyField(
                related_name="distributors",
                through="goods.ProductDistributor",
                to="goods.product",
            ),
        ),
    ]
