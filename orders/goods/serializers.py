from rest_framework import serializers
from .models import Product, ProductDistributor, Distributor, User, Basket, \
    OrderConfirmation, Address, OrderMeta, OrderHistory


class ProductDistributorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDistributor
        fields = ['distributor', 'price', 'delivery_price', 'quantity']


class ProductParameterSerializer(serializers.ModelSerializer):
    product_distributors = ProductDistributorSerializer(many=True)
    prod_parameters = serializers.StringRelatedField(many=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'product_distributors', 'prod_parameters']


class BasketSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с корзиной
    """
    class Meta:
        model = Basket
        fields = ['id', 'product', 'distributor', 'price', 'quantity', 'sum', 'total_price']
        read_only_fields = ['id', 'price', 'sum', 'total_price']

    def create(self, validated_data):

        # Получить набор данных из БД для сопоставления записей в корзине с таблицей Product и Distributor
        product = Product.objects.get(name=validated_data['product'])
        user = User.objects.get(last_name=validated_data['distributor'])
        distributor = Distributor.objects.get(user=user.id)

        # Получить стоимость доставки для расчета read_only_fields
        delivery_price = ProductDistributor.objects.filter(distributor=distributor).get(product=product).delivery_price
        price = ProductDistributor.objects.filter(distributor=distributor).get(product=product).price

        # Добавить недостающие записи в сериализатор
        validated_data['price'] = price
        validated_data['sum'] = validated_data['quantity'] * validated_data['price']
        validated_data['total_price'] = validated_data['sum'] + delivery_price

        return Basket.objects.create(**validated_data)

    def update(self, instance, validated_data):
        product = Product.objects.get(name=instance.product)
        instance.quantity = validated_data.get('quantity', instance.quantity)

        # Проверка на случай, если поле distributor не передается в методе PATCH
        if validated_data.get('distributor'):
            user = User.objects.get(last_name=validated_data.get('distributor'))
            instance.distributor = validated_data.get('distributor')
        else:
            user = User.objects.get(last_name=instance.distributor)
        distributor = Distributor.objects.get(user=user.id)  # Получить distributor из БД

        # получение недостающих данных из БД
        delivery_price = ProductDistributor.objects.filter(distributor=distributor).get(product=product).delivery_price
        price = ProductDistributor.objects.filter(distributor=distributor).get(product=product).price

        # Сохранение расчетных данных в БД
        instance.sum = instance.quantity * price
        instance.total_price = instance.sum + delivery_price
        instance.save()

        return instance

    def validate(self, attr):

        # Получение предельного количества товаров для выбранного дистрибьютора для методов PATCH и POST
        if self.context['request'].method == 'PATCH':
            pk = self.context['request'].parser_context['kwargs']['pk']
            prod_in_basket = Basket.objects.get(pk=pk).product
            product = Product.objects.get(name=prod_in_basket).id
            quantity_limit = ProductDistributor.objects.get(product=product).quantity
        else:
            product = Product.objects.get(name=attr.get('product')).id
            quantity_limit = ProductDistributor.objects.get(product=product).quantity

        # проверка на наличие дистрибьютора в запросе
        if attr.get('distributor'):
            user = User.objects.get(last_name=attr.get('distributor'))

            # Проверка, что пользователь является дистрибьютором
            if user.type != 'distributor':
                raise serializers.ValidationError('The user is not distributor')
            distributor = Distributor.objects.get(user=user)

            # Проверка, что дистрибьютор готов принимать заказы
            if not distributor.status:
                raise serializers.ValidationError('Now the distributor is unavailable')

        # Проверка достаточного количества товара от дистрибьютора, что выполнить заказ
        if attr.get('quantity'):
            if attr.get('quantity') > quantity_limit:
                raise serializers.ValidationError(f'Not enough items, max quantity is {quantity_limit}')

        return attr


class AddressSerializer(serializers.ModelSerializer):
    """
    Сериализатор для наполнения модели Address при подтверждении заказа
    """
    class Meta:
        model = Address
        fields = ['city', 'street', 'building', 'office']


class OrderConfirmationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для подтверждения заказа от покупателя
    """
    address = AddressSerializer()

    class Meta:
        model = OrderConfirmation
        fields = ['last_name', 'first_name', 'middle_name', 'email', 'phone', 'address', 'basket']

    def create(self, validated_data):
        is_existing_customer = OrderConfirmation.objects.filter(email=validated_data['email']).exists()
        address_data = validated_data.pop('address')

        # Проверка, чтобы избежать многократной записи одинаковых адресов в модель Address
        if is_existing_customer:
            previous_order = OrderConfirmation.objects.filter(email=validated_data['email']).first()
            address = previous_order.address
        else:
            address = Address.objects.create(**address_data)
        basket = Basket.objects.get(id=validated_data['basket'])
        confirmation = OrderConfirmation.objects.create(address=address, **validated_data)
        OrderMeta.objects.create(basket=basket,
                                 order_confirmation=confirmation,
                                 status='new')

        return confirmation


class OrderChangeStatusSerializer(serializers.ModelSerializer):
    """
    Serializer для изменения статуса заказа с последующим сохранением информации о заказе в
    в модели с историей заказов
    """
    class Meta:
        model = OrderMeta
        fields = ['status']

    def update(self, instance, validated_data):

        # в модель OrderHistory сохраняется только та информация о заказах, которым присвоен статус "доставлен"
        # или "отменен"
        if validated_data['status'] in ['cancelled', 'delivered']:
            result_price = instance.basket.total_price
            OrderHistory.objects.get_or_create(result_price=result_price,
                                               order=instance,
                                               order_confirmation=validated_data['status'])
        instance.status = validated_data.get('status', instance.status)
        instance.save()

        return instance


class PriceForOrderMetaSerializer(serializers.ModelSerializer):
    """
    Вспомогательный serializer для OrderMetaSerializer, для вывода информации о полной цене
    """
    class Meta:
        model = Basket
        fields = ['total_price']


class OrderMetaSerializer(serializers.ModelSerializer):
    """
    Serializer для вывода информации о заказах
    """
    basket = PriceForOrderMetaSerializer()

    class Meta:
        model = OrderMeta
        fields = ['id', 'date', 'basket', 'status']
        read_only_fields = ['id', 'date', 'basket', 'status']


class OrderHistorySerializer(serializers.ModelSerializer):
    """
    Serializer для вывода информации об истории закрытых заказов
    """

    class Meta:
        model = OrderHistory
        fields = ['id', 'order', 'order_confirmation', 'result_price']
        read_only_fields = ['id', 'order', 'order_confirmation', 'result_price']
