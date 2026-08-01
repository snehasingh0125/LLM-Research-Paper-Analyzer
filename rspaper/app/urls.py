from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("password-reset-request/", views.password_reset_request_view, name="password_reset_request"),
    path("password-reset/<uidb64>/<token>/", views.password_reset_confirm_view, name="password_reset_confirm"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("upload/", views.upload_paper_view, name="upload_paper"),
    path("paper/<int:paper_id>/", views.paper_detail_view, name="paper_detail"),
    path("paper/<int:paper_id>/summarize/", views.summarize_paper_view, name="summarize_paper"),
    path("paper/<int:paper_id>/select-compare/", views.select_comparison_papers_view, name="select_comparison_papers"),
    path("paper/<int:paper_id>/compare/", views.compare_papers_view, name="compare_papers"),
    path("search/", views.search_papers_view, name="search_papers"),
    path("voice-command/", views.voice_command_view, name="voice_command"),
    path("slides/<int:paper_id>/", views.generate_slides_view, name="generate_slides"),
    path("slides/<int:paper_id>/", views.generate_slides_view, name="view_slides"),
]
