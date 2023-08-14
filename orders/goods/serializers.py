from rest_framework import serializers
from .models import Parameter, Product, ProductParameter, ProductDistributor, Distributor, User


class ProductParameterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для вывода значения параметра в карточку товара
    """
    class Meta:
        model = ProductParameter
        fields = ['value']


class ParameterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для вывода конкретного параметра в карточку товара
    """
    prod_parameters = ProductParameterSerializer(many=True)

    class Meta:
        model = Parameter
        fields = ['name', 'prod_parameters']


class UserDistributorSerializer(serializers.ModelSerializer):
    """
    Сериализатор для вывода данных дистрибьютора в карточку товара
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'company']


class DistributorSerializer(serializers.ModelSerializer):
    """
    Сериализатор для вывода дистрибьютора в карточку товара
    """
    user = UserDistributorSerializer()

    class Meta:
        model = Distributor
        fields = ['user', 'status']


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для представления списка карточек товаров
    """
    parameters = ParameterSerializer(many=True)
    distributors = DistributorSerializer(many=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'price_with_delivery', 'quantity', 'parameters', 'distributors']


class RegisterSerializer(serializers.ModelSerializer):

    pass
