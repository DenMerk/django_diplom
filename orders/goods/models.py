from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.contrib.auth.models import AbstractUser


STATUS_CHOICES = (
    ('new', 'новый'),
    ('paid', 'оплачен'),
    ('delivered', 'доставлен'),
    ('cancelled', 'отменен'),
)

USER_TYPE_CHOICES = (
    ('distributor', 'поставщик'),
    ('customer', 'покупатель'),
)


class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
        Стандартная модель пользователей
    """
    objects = UserManager()
    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'email'
    middle_name = models.CharField(max_length=150, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(max_length=150, validators=[username_validator])
    email = models.EmailField('email address', unique=True)
    type = models.CharField(verbose_name='Тип пользователя',
                            choices=USER_TYPE_CHOICES,
                            max_length=20,
                            default='customer')
    company = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    address = models.ForeignKey('Address', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)


class Distributor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='users')
    status = models.BooleanField(default=True)
    product = models.ManyToManyField('Product', related_name='distributors', through='ProductDistributor')

    def __str__(self):
        return self.user


class Parameter(models.Model):
    name = models.CharField(max_length=50)
    product = models.ManyToManyField('Product', related_name='parameters', through='ProductParameter')

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Параметры'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    parameter = models.ManyToManyField(Parameter, related_name='products', through='ProductParameter')
    distributor = models.ManyToManyField(Distributor, related_name='products', through='ProductDistributor')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    parameter_name = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name='prod_parameters')
    product_name = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prod_parameters')
    value = models.CharField(max_length=50)

    def __str__(self):
        return f'{self.parameter_name}: {self.value}'


# class Order(models.Model):
#     data = models.DateTimeField(auto_now_add=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES)
#     total_price = models.FloatField()
#     product = models.ManyToManyField(Product, related_name='order', through='ProductOrder')
#
#     class Meta:
#         verbose_name = 'Заказ'
#         verbose_name_plural = 'Заказы'

#
# class ProductOrder(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='products')
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='products')
#     quantity = models.PositiveIntegerField()


class ProductDistributor(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_distributors')
    distributor = models.ForeignKey(Distributor, on_delete=models.CASCADE, related_name='product_distributors')
    price = models.FloatField(default=10000)
    delivery_price = models.FloatField(blank=True, default=0)
    quantity = models.PositiveIntegerField(default=1)

    # def __str__(self):
    #     return self.distributor


# class OrderedProduct(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='ordered_products')
#     distributor = models.ForeignKey(Distributor, on_delete=models.CASCADE, related_name='ordered_products')
#     quantity = models.PositiveIntegerField()


class Address(models.Model):
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=100)
    building = models.CharField(max_length=10)
    office = models.CharField(max_length=10)

    class Meta:
        verbose_name = 'Адрес'
        verbose_name_plural = 'Адреса'


class Basket(models.Model):
    product = models.CharField(max_length=100)
    distributor = models.CharField(max_length=100)
    price = models.FloatField(default=10000)
    quantity = models.PositiveIntegerField()
    sum = models.FloatField()
    total_price = models.FloatField(default=10000)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f"{self.distributor} - {self.product}"


class OrderConfirmation(models.Model):
    basket = models.IntegerField()
    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=25)
    middle_name = models.CharField(max_length=30)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='order_confirmations')


class OrderMeta(models.Model):
    basket = models.OneToOneField(Basket, on_delete=models.CASCADE)
    order_confirmation = models.OneToOneField(OrderConfirmation, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)


class OrderHistory(models.Model):
    order = models.OneToOneField(OrderMeta, on_delete=models.DO_NOTHING)
    result_price = models.FloatField()
    order_confirmation = models.CharField(max_length=20, choices=STATUS_CHOICES)




