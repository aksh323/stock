from django.shortcuts import render
from django.http import HttpResponse
import subprocess
import os,json
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def main(request):
    if request.method=='POST':
        data=json.loads(request.body)
        check = subprocess.run(["python","aalgo_SmartAPI.py","--api_key",data.get("api_key"),"--api_secret",
                                data.get("api_secret"),"--client_code",data.get("client_code"),"--mpin",data.get("mpin"),
                                "--totp_code",data.get("totp_code")
                                ], capture_output = True,text = True)
        
        return HttpResponse(str(check.stdout))
