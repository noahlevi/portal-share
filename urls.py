from django.urls import path

from .views import (
	# user
    UserCreditsView,
    UserOrdersView,
    UserApiKeyView,
    UserLogoutView,

	# admin
    AdminHomeView,

    # manage credits
    # AdminUserCreditsView,
    AdminAddOrUpdateCreditsView,
    AdminDeleteCreditsView,

    # manage orders
    # AdminUserOrdersView,
    # AdminAddOrderView,
    # AdminUpdateOrderView,
    AdminAddOrUpdateOrderView,
    AdminDeleteOrderView,
)

app_name = "portal"
urlpatterns = [
    # Customer Interface
    path("credits/", UserCreditsView.as_view(), name="user-credits"),
    path("orders/", UserOrdersView.as_view(), name="user-orders"),
    path("api-key/", UserApiKeyView.as_view(), name="user-api-key"),
    path("logout/", UserLogoutView.as_view(), name="user-logout"),

    # Operational Admin Interface
    path("admin/", AdminHomeView.as_view(), name="admin-home"),

    # manage credits
    # path("admin/user/<int:user_id>/credits", AdminUserCreditsView.as_view(), name="admin-user-credits"),
    path("admin/user/<int:user_id>/credits/delete/<int:credits_id>", AdminDeleteCreditsView.as_view(), name="admin-delete-credits"),
    path("admin/user/credits/add-or-update", AdminAddOrUpdateCreditsView.as_view(), name="admin-add-or-update-credits"),
    
    # manage orders
    # path("admin/user/<int:user_id>/orders", AdminUserOrdersView.as_view(), name="admin-user-orders"),
    path("admin/user/<int:user_id>/order/delete/<int:order_id>", AdminDeleteOrderView.as_view(), name="admin-delete-order"),
    path("admin/user/order/add-or-update", AdminAddOrUpdateOrderView.as_view(), name="admin-add-or-update-order"),

    # path("admin/user/create", AdminCreateUserView.as_view(), name="admin-create-user"),
    # path("admin/user/<int:user_id>", AdminUserCard.as_view(), name="user-card"),
    # path("admin/user/<int:user_id>/update", AdminUpdateUser.as_view(), name="update-user"),
    # path("admin/company/<int:company_id>", AdminCompanyCard.as_view(), name="company-card"),
    # path("admin/company/create", AdminCreateCompany.as_view(), name="create-company"),
    # path("admin/company/<int:company_id>/update", AdminUpdateCompany.as_view(), name="update-company"),

    # API
    # path("user/<int:user_id>/add-credits", AddCredits.as_view(), name="add-credits"),
    # path("user/<int:user_id>/update-credits/<int:credits_id>", UpdateCredits.as_view(), name="update-credits"),
    # path("user/<int:user_id>/add-order", AddOrder.as_view(), name="add-order"),
    # path("user/<int:user_id>/update-order/<int:order_id>", UpdateOrder.as_view(), name="update-order"),
    # path("user/<int:user_id>/delete", DeleteUser.as_view(), name="delete-user"),
    # path("user/<int:user_id>/update", UpdateUser.as_view(), name="update-user"),
    # path("user/create", CreateUser.as_view(), name="update-user"),
    # path("company/create", CreateCompany.as_view(), name="create-company"),
    # path("company/<int:company_id>/delete", DeleteCompany.as_view(), name="delete-company"),
    # path("company/<int:company_id>/update", UpdateCompany.as_view(), name="update-company"),
]
