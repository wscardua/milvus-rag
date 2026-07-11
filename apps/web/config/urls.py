from django.urls import path

from chat import views as chat_views
from documents import views as doc_views
from organization import views as org_views
from query import views as query_views
from system import views as system_views

urlpatterns = [
    path("", doc_views.document_list, name="document_list"),
    path("upload/", doc_views.document_upload, name="upload"),
    path("documentos/<uuid:document_id>/", doc_views.document_detail, name="document_detail"),
    path("documentos/<uuid:document_id>/arquivo/", doc_views.document_file, name="document_file"),
    path("consulta/", query_views.consulta, name="consulta"),
    path("consulta/feedback/", query_views.query_feedback, name="query_feedback"),
    path("chat/", chat_views.chat, name="chat"),
    path("chat/<uuid:conversation_id>/", chat_views.chat, name="chat_thread"),
    path("squads/", org_views.squads, name="squads"),
    path("processos/", org_views.processes, name="processes"),
    path("logs/", system_views.logs, name="logs"),
]
