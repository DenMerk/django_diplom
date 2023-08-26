from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework_yaml.parsers import YAMLParser
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from rest_framework.views import APIView
from .models import User, Product, Parameter, ProductParameter, Distributor, ProductDistributor, Address, Basket, \
    OrderConfirmation, OrderMeta, OrderHistory
from .serializers import ProductParameterSerializer, BasketSerializer, OrderConfirmationSerializer, \
    OrderMetaSerializer, OrderChangeStatusSerializer, OrderHistorySerializer
from orders.settings import EMAIL_HOST_USER


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    parser_classes = [YAMLParser]

    def get(self, request):
        return Response({'status': 'GET-OK'})

    def post(self, request, *args, **kwargs):

        # Проверка, что пользователь аутенфицирован
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # проверка, что только дистрибьютор может добавлять (обновлять) перечень товаров
        if request.user.type != 'distributor':
            return JsonResponse({'Status': False, 'Error': 'Only for distributors'}, status=403)

        # получение объекта дистрибьютора
        distributor = Distributor.objects.get(user=request.user)
        obj_good = request.data.get('goods')
        number = 0
        while number < len(obj_good):
            # наполнение модели Product
            product, _ = Product.objects.get_or_create(name=obj_good[number].get('name'))
            product.name = obj_good[number].get('name')
            # product.price_with_delivery = obj_good[number].get('price_rrc')
            # product.quantity = obj_good[number].get('quantity')
            product.save()

            dict_with_parameters = obj_good[number].get('parameters')

            # удаление старой записи в модели ProductParameter
            ProductParameter.objects.filter(product_name=product.id).delete()

            # цикл для заполнения моделей Parameter, ProductParameter
            for key, value in dict_with_parameters.items():
                parameter, _ = Parameter.objects.get_or_create(name=key)
                ProductParameter.objects.create(product_name=product,
                                                parameter_name=parameter,
                                                value=value)

            # Проверка, что поля цен валидны
            if obj_good[number].get('price_rrc') <= obj_good[number].get('price'):
                return JsonResponse({'Status': False, 'Error': 'Incorrect prices'}, status=400)

            delivery_price = obj_good[number].get('price_rrc') - obj_good[number].get('price')

            # удаление старой записи в модели ProductDistributor
            ProductDistributor.objects.filter(product=product.id).delete()

            # Наполнение модели ProductDistributor
            ProductDistributor.objects.create(product=product,
                                              distributor=distributor,
                                              price=obj_good[number].get('price'),
                                              quantity=obj_good[number].get('quantity'),
                                              delivery_price=delivery_price)
            number += 1
        return Response({'status': 'POST-OK'})


class LoginAPIView(APIView):
    """
    Класс для авторизации пользователя
    """

    def post(self, request):

        # Проверка наличия пользователя и корректность введенного email
        if not User.objects.filter(email=request.data.get('email')):
            return JsonResponse({'Status': False, 'Error': 'A user with that email does not exist'}, status=401)

        # Получение пользователя
        user = User.objects.get(email=request.data.get('email'))

        # Проверка корректности введенного пароля
        if not user.check_password(request.data.get('password')):
            return JsonResponse({'Status': False, 'Error': 'Wrong password, login declined'}, status=401)

        return Response({'status': 'POST-OK'})

    def delete(self, request, pk):
        # Метод для удаления пользователя

        # Проверка авторизации пользователя перед удалением аккаунта
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Deletion declined. Authentication required'}, status=401)

        # Проверка, что пользователь хочет удалить свой аккаунт
        if Token.objects.get(user=pk) != request.auth:
            return JsonResponse({'Status': False, 'Error': 'Permission denied. Only owner can delete the account'},
                                status=403)
        user = User.objects.get(email=request.user.email)
        Address.objects.get(user=user).delete()

        # Проверка на необходимость удаления связанной записи в модели Distributor
        if request.user.type == 'distributor':
            Distributor.objects.get(user=user).delete()
        User.objects.get(email=request.user.email).delete()

        return Response({'status': 'DELETE-OK'})

    def patch(self, request, pk):
        # Метод для изменения статуса дистрибутора

        # Проверка, что пользователь изменяет статус своего аккаунта
        if Token.objects.get(user=pk) != request.auth:
            return JsonResponse({'Status': False, 'Error': 'Permission denied. Only owner can update the account data'},
                                status=403)

        distributor = Distributor.objects.get(user=request.user)
        distributor.status = request.data.get('status')
        distributor.save()

        return Response({'status': 'PATCH-OK'})


class ProductViewSet(viewsets.ViewSet):
    """
    Класс для представления товаров
    """
    def list(self, request):
        queryset = Product.objects.all()
        serializer = ProductParameterSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = Product.objects.all()
        product = get_object_or_404(queryset, pk=pk)
        serializer = ProductParameterSerializer(product)
        return Response(serializer.data)


class RegisterAPIView(APIView):
    """
    Класс для регистрации нового пользователя (создание аккаунта)
    """
    def post(self, request, *args, **kwargs):
        user_obj = request.data

        # Проверка, что аккаунта с данным email не существует
        if User.objects.filter(email=user_obj.get('email')).exists():
            return JsonResponse({'Status': False, 'Error': 'The user already exists'}, status=400)

        # Проверка на корректность введенного пароля
        if not user_obj.get('password') == user_obj.get('password_repeat'):
            return JsonResponse({'Status': False, 'Error': 'An error occurs with typing password. Try again'},
                                status=400)

        address = Address.objects.create(
            city=user_obj.get('city'),
            street=user_obj.get('street'),
            building=user_obj.get('building'),
            office=user_obj.get('office')
        )

        user = User.objects.create_user(email=user_obj.get('email'), password=user_obj.get('password'))
        user.first_name = user_obj.get('first_name')
        user.last_name = user_obj.get('last_name')
        user.middle_name = user_obj.get('middle_name')
        user.username = user_obj.get('username')
        user.company = user_obj.get('company')
        user.type = user_obj.get('type')
        user.phone = user_obj.get('phone')
        user.address = address
        user.save()

        if user_obj.get('type') == 'distributor':
            Distributor.objects.create(user=user,
                                       status=user_obj.get('status'))

        Token.objects.create(user=user)  # Создание токена для нового пользователя

        # Параметры для отправки email с подтверждением регистрации
        message = f"Здравствуйте, {user_obj.get('first_name')} {user_obj.get('last_name')}! \n" \
                  f"Спасибо за регистрацию \n" \
                  f"Ваш логин - {user_obj.get('email')} \n"
        subject = f'Подтверждение регистрации'
        from_email = EMAIL_HOST_USER
        recipient_list = [user_obj.get('email')]
        send_mail(subject, message, from_email, recipient_list)  # непосредственно отправка email

        return Response({'status': 'POST-OK'})


class BasketViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с корзиной
    Реализованы методы GET, POST, PATCH, DELETE
    """
    queryset = Basket.objects.all()
    serializer_class = BasketSerializer


class OrderConfirmationViewSet(viewsets.ModelViewSet):
    """
    Представление для получения POST запроса с подтверждением заказа
    """
    queryset = OrderConfirmation
    serializer_class = OrderConfirmationSerializer


class OrderAPIView(APIView):
    """
    Представление для вывода сформированного заказа
    """
    def get(self, request, pk):
        """
        Метод для получения заказа, pk -> id из модели OrderMeta
        :param request: Request
        :param pk: int
        :return: Response
        """
        order = OrderMeta.objects.get(id=pk)
        confirmation = order.order_confirmation
        basket = order.basket
        context = {
            'order_number': order.id,
            'date': order.date,
            'status': order.status,
            'product': basket.product,
            'distributor': basket.distributor,
            'price': basket.price,
            'quantity': basket.quantity,
            'sum': basket.sum,
            'customer': f'{confirmation.last_name} {confirmation.first_name} {confirmation.middle_name}',
            'email': confirmation.email,
            'phone': confirmation.phone,
        }

        # Параметры для отправки email с параметрами заказа для клиента
        message = f"Спасибо за заказ \n" \
                  f"Параметры заказа:\n" \
                  f"Номер заказа - {order.id}\n" \
                  f"Ваш заказ - {order.basket.product} \n" \
                  f"Поставщик - {order.basket.distributor} \n" \
                  f"Количество - {order.basket.price} \n" \
                  f"Итоговая цена - {order.basket.sum}"
        subject = f'Ваш заказ № {order.id} принят'
        from_email = EMAIL_HOST_USER
        recipient_list = [confirmation.email]
        send_mail(subject, message, from_email, recipient_list)  # отправка email клиенту

        # Рассылка нового заказа на почту администратора
        message_to_admin = f"Поступил новый заказ \n" \
                           f"Параметры заказа: \n" \
                           f"Номер заказа - № {order.id} \n" \
                           f"Наименование товара - {order.basket.product} \n" \
                           f"Поставщик - {order.basket.distributor}\n" \
                           f"Покупатель - {confirmation.last_name} {confirmation.first_name} " \
                           f"{confirmation.middle_name} \n" \
                           f"Количество - {order.basket.price} \n" \
                           f"Итоговая цена - {order.basket.sum} \n" \
                           f"Адрес - {confirmation.address.city} {confirmation.address.street}, " \
                           f"building - {confirmation.address.building}, office - {confirmation.address.office}"

        subject_to_admin = f'Новый заказ № {order.id}'
        from_email = EMAIL_HOST_USER
        admin_email = User.objects.filter(is_superuser=True).first().email
        recipient_list = [admin_email]
        send_mail(subject_to_admin, message_to_admin, from_email, recipient_list)  # отправка email админу

        return Response(data=context, status=200)


class OrderMetaViewSet(viewsets.ModelViewSet):
    """
    Представление для отображения заказов
    """
    queryset = OrderMeta.objects.all()
    serializer_class = OrderMetaSerializer


class OrderChangeStatusViewSet(viewsets.ModelViewSet):
    """
    Представление для изменения статуса заказа
    """
    queryset = OrderMeta
    serializer_class = OrderChangeStatusSerializer


class OrderHistoryViewSet(viewsets.ModelViewSet):
    """
    Представление для отображения истории заказов
    """
    queryset = OrderHistory.objects.all()
    serializer_class = OrderHistorySerializer
