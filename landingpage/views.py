from django.shortcuts import render

def landingpage_home(request):
    return render(request, 'landingpage/landingpage_home.html')
