import json

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import View

from graphql.core.error import GraphQLError, format_error


def form_error(error):
    if isinstance(error, GraphQLError):
        return format_error(error)
    return error


class GraphQLView(View):
    schema = None

    @staticmethod
    def format_result(result):
        data = {'data': result.data}
        if result.errors:
            data['errors'] = list(map(form_error, result.errors))

        return data

    def response_errors(self, *errors):
        errors = [{
            "message": str(e)
        } for e in errors]
        return HttpResponse(json.dumps({'errors': errors}), content_type='application/json')

    def execute_query(self, request, query, *args, **kwargs):
        if not query:
            return self.response_errors(Exception("Must provide query string."))
        else:
            try:
                result = self.schema.execute(query, *args, **kwargs)
                data = self.format_result(result)
            except Exception as e:
                if settings.DEBUG:
                    raise e
                return self.response_errors(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get(self, request, *args, **kwargs):
        query = request.GET.get('query')
        return self.execute_query(request, query or '')

    @staticmethod
    def get_content_type(request):
        meta = request.META
        return meta.get('CONTENT_TYPE', meta.get('HTTP_CONTENT_TYPE', ''))

    def post(self, request, *args, **kwargs):
        content_type = self.get_content_type(request)
        if content_type == 'application/json':
            try:
                received_json_data = json.loads(request.body.decode())
                query = received_json_data.get('query')
            except ValueError:
                return self.response_errors(ValueError("Malformed json body in the post data"))
        elif content_type == 'application/graphql':
            query = request.body.decode()
        else:
            query = request.POST.get('query') or request.GET.get('query')
        return self.execute_query(request, query or '')
