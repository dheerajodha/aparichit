from django.shortcuts import render, redirect,HttpResponseRedirect
from django.contrib.auth import authenticate, login,logout
from django.http import HttpResponse,JsonResponse
from django.contrib.auth.models import User
from app.models import launchpad,data
from django.core import serializers
from django.core.files.storage import default_storage
import json
import pickle
import csv
import pandas as pd
from collections import defaultdict
import math
from . import utils
from . import lstm
from . import cosys

def home(request):
    return render(request,'app/home.html')

def log(request):
    if request.method == 'POST':

        username = request.POST['username']
        password = request.POST['password']
        # print(username,password)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
        else:
            pass
        return render(request,'app/home.html')
            # return JsonResponse({'success': 'true'})
def logo(request):
    logout(request)
    return render(request,'app/home.html')

def signup(request):
    if request.method == 'POST':
        # print( request.POST['username'])
        us=User.objects.create_user( request.POST['username'],  request.POST['email'],  request.POST['password'])
        us.save()  
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
        else:
            pass
        return render(request,'app/home.html')

def launch(request):
    if request.method == 'GET':
        id=request.user.username
        data=launchpad.objects.filter(user=id)  
        print("\n\n\n",data)
        data=serializers.serialize('json', data)
        dat =   data.replace("'","\"")
        d = json.loads(dat)
        return render(request,'app/launchpad.html',{'launch_pads':d})
    elif request.method == 'POST':
        return JsonResponse({'success': 'true'})

def del_launchpad(request):
    if request.method == 'POST':
        instance = launchpad.objects.get(user=request.user.username,name=request.POST.get('DeleteButton'))
        instance.delete()
        # return JsonResponse({'success': 'true'})
        return HttpResponseRedirect("launchpad")

def del_data(request):
    if request.method == 'POST':
        instance = data.objects.get(user=request.user.username,inputfile_path=request.POST.get('DeleteButton'))
        instance.delete()
        default_storage.delete('app/data/'+ request.user.username+'/' +request.POST.get('DeleteButton'))
        # return JsonResponse({'success': 'true'})
        return HttpResponseRedirect("upload")

def upload(request):
    if request.method == 'GET':
        id=request.user.username
        instance=data.objects.filter(user=id)  
        instance=serializers.serialize('json', instance)
        dat =   instance.replace("'","\"")
        d = json.loads(dat)
        return render(request,'app/upload.html',{'file_added':d})
    elif request.method == 'POST':
        # return JsonResponse({'success': 'true'})
        try:
            myfile = request.FILES['file']
        except:
            pass
        id=request.user.username        
        if  data.objects.filter(user=id,inputfile_path=myfile.name).count()==0:
            file_name = default_storage.save('app/data/'+ request.user.username+'/' +myfile.name, myfile)  
            instance=data(user=request.user.username,inputfile_path=myfile.name)
            instance.save()
        else:
            print("file already exist")
        return HttpResponseRedirect("upload")

def cluster(request):
    if request.method == 'GET':
        # print("cluster")
        try:
            myfile=request.session['prediction']
            id=request.user.username
            instance=data.objects.filter(user=id,inputfile_path=myfile)  
            instance=serializers.serialize('json', instance)
            dat = instance.replace("'","\"")
            d = json.loads(dat)
            d = d[0]['fields']
        except:
            d={}
        return render(request,'app/cluster.html',{'pred':d.get('prediction','')})
    elif request.method == 'POST':
        id=request.user.username
        with open("app/model/model", 'rb') as f:
            model = pickle.load(f)
        #predict goes here
        myfile=request.POST.get('file[]')
        if(type(myfile)==list):
            myfile=myfile[-1]
        x_test = utils.preprocess('app/Data/'+id + '/' + myfile)
        pred_object_no = model.predict(x_test)
        pred_object = {
            0 : 'Helicopter',
            1 : 'AirPlane'
        }
        return_item_1 = pred_object[pred_object_no[0]]
        obj=data.objects.get(user=id,inputfile_path=myfile)
        obj.prediction=return_item_1
        # obj.save()
        request.session['prediction'] = myfile
        request.session['visualize'] = myfile
        prediction_df, last_true = lstm.process('app/Data/'+id + '/' + myfile)
        obj.processedfile_path='processed_' + myfile
        obj.save()
        #TODO : Altitude jugaad
        prediction_df.to_csv('app/Data/'+id + '/processed_' + myfile)
        # return render(request,'app/cluster.html')
        # return HttpResponseRedirect("home")
        return JsonResponse({'success': 'true'})

def visualize(request):
    if request.method == 'GET':
        #pass data for map
        myfile=request.session['file']
        id=request.user.username
        df = pd.read_csv('app/Data/'+id + '/' + myfile, index_col = 0)
        mylist = df[['Lat','Long']].values 
        return render(request,'app/visualize.html',{'csv':mylist})
    elif request.method == 'POST':
        myfile=request.POST.get('file[]')
        if(type(myfile)==list):
            myfile=myfile[-1]
        request.session['file']=myfile
        return JsonResponse({'success': 'true'})

def new_lpd(request):
    if request.method == 'GET':
        return render(request, 'app/new_lpd.html')
    elif request.method == 'POST':
        id = request.user.username
        print(request.POST)
        obj = launchpad(user= id ,name= request.POST['name'], latitude = request.POST['latitude'], 
            longitude = request.POST['longitude'], missile = request.POST['missile'])
        obj.save()
    return redirect('launchpad')

def new_file(request):
    return render(request,'app/new_file.html') 

def launch_attack(request):
    if request.method == 'GET':
        return render(request,'app/launch.html')
    elif request.method == 'POST':
        id = request.user.username
        myfile = request.session['prediction']
        lat_lpd, long_lpd = (54.6872, 25.2797) ##fetch from frontend
        df = pd.read_csv('app/Data/' + id +'/' + myfile, index_col = 0)
        lat_i, long_i, alt = intersect(df, lat_lpd,long_lpd)
        speed = 1027.778 #(m/s) ##later configure missile param...
        #speed if for Bhramos
        dist = distance(lat_lpd, long_lpd, lat_i, long_i)
        time =  dist/speed #secs 
        angle = math.atan(alt/dist)
        ##send time and angle to frontend xD
        ## draw straight line from point (lat_i, long_i to lat_lpd, long_lpd)
        return render(request,'app/launch.html')
    
