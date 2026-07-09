from django.urls import path

from documents import views as doc_views
from organization import views as org_views
from query import views as query_views

urlpatterns = [
    path("", doc_views.document_list, name="document_list"),
    path("upload/", doc_views.document_upload, name="upload"),
    path("documentos/<uuid:document_id>/", doc_views.document_detail, name="document_detail"),
    path("consulta/", query_views.consulta, name="consulta"),
    path("squads/", org_views.squads, name="squads"),
    path("processos/", org_views.processes, name="processes"),
]
