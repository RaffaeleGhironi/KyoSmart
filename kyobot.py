#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import platform
from threading import Timer
import  threading as th
import time
from datetime import datetime
from distutils.command.config import config
from subprocess import getoutput
from tty import CFLAG

import cv2
import ffmpeg
import psutil
import RPi.GPIO as GPIO
import telebot
from telebot import custom_filters, types
from telebot.callback_data import CallbackData, CallbackDataFilter
from telebot.custom_filters import AdvancedCustomFilter
from telebot.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

GPIO.setwarnings(False)
# Definizione dei pin I/O in base al nome del pin
pin_area1   =   2                                       # Pin cambio stato Area1
pin_area2   =   17                                      # Pin cambio stato Area2
pin_oc1     =   13                                      # Pin stato Area1
pin_oc2     =   19                                      # Pin stato Area2
pin_oc3     =   26                                      # Pin stato Guasti
pin_no      =   6                                       # Pin stato Allarme
pin_z1      =   27                                      # Pin Zona1
pin_z2      =   22                                      # Pin Zona2
pin_z3      =   10                                      # Pin Zona3
pin_z4      =   9                                       # Pin Zona4
pin_z5      =   11                                      # Pin Zona5
pin_z6      =   5                                       # Pin Zona6


stato_area1=False
stato_area2=False
stato_allarme=False
stato_guasti=False

# Settaggio dei pin I/O
GPIO.setmode(GPIO.BCM)                                  # Use Board pin numbering
GPIO.setup(pin_area1, GPIO.OUT)                         
GPIO.setup(pin_area2, GPIO.OUT)                         
GPIO.setup(pin_oc1  , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_oc2  , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_oc3  , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_no   , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_z1   , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_z2   , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_z3   , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_z4   , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_z5   , GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(pin_z6   , GPIO.IN, pull_up_down=GPIO.PUD_UP)


 
def data_ora():
    localtime = time.asctime( time.localtime(time.time()) )
    return localtime

def log(testo):
    file_log = open('log.txt',"a")
    file_log.write("\n"+data_ora()+" -->  "+testo)
    file_log.close()

# Leggo il Json di configurazione
def leggi_config():
    file_json = open('config.json')
    cfgjsn=""
    try:
        cfgjsn=json.load(file_json)
    except:
        print('json vuoto')
    return cfgjsn

# leggi il file di configurazione  
cfgjsn=leggi_config()
# Inizializzo il bot  
bot = telebot.TeleBot(cfgjsn['token'])

print('KyoBot si è avviato correttamente')
log('KyoBot si è avviato correttamente')


# Classe usata per i filtri delle CallBack
class CallbackFilter(AdvancedCustomFilter):
    key = 'config'
    def check(self, call: CallbackQuery, config: CallbackDataFilter):
        return config.check(query=call)

# Classe per il CountDown
class CountDown(object):
    def __init__(self, id=None, current_status=None):
        self.id = id
        self.current_status = current_status
        self.stato=''
        
    def timeout(self):
        #print("time over for", self.id)
        self.stato=''
        FineTimer_ai()

    def start_timer(self,tempo):
        if self.stato=='start' :
            return
        self.stato='start'
        self.t = Timer(tempo, self.timeout)  # changed to 5 seconds for demo                                                 
                                         # `self.timeout` instead of `timeout`
        self.t.start()
        print ('Start -> ',time.asctime( time.localtime(time.time())))

    def reset_timer(self):
        self.t.cancel()      # cancel old timer
        print ('Reset -> ',time.asctime( time.localtime(time.time())))
        self.start_timer()   # and start a new one
        
    def stop_timer(self):
        self.t.cancel()      # cancel old timer
        self.stato=''
        print ('Stop -> ',time.asctime( time.localtime(time.time())))


def get_size(bytes, suffix="B"):
    #Funzione Usata per Convertire i valori del disco e della memoria
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor
def stato_servizi(servizio):
    status='fail'       # se non arriva nulla restituisco Fail
    if servizio=='vpn':
        status = getoutput(f"systemctl show VpnKyoBot.service -p SubState").split("=")[1].lower()
    elif servizio=='ssh':
        status = getoutput(f"systemctl show sshd -p SubState").split("=")[1].lower()
    elif servizio=='kyobot':
        status = getoutput(f"systemctl show KyoBot.service -p SubState").split("=")[1].lower()
    return status
def gest_servizio(servizio,azione):
    stato_servizio=stato_servizi(servizio)
    if azione=='start':
        if stato_servizio=='running':
            print ( 'Servizio',servizio,' già Attivo')
            return 'già Attivo'
        else:
            print ('Avvio il servizio ',servizio)
            if servizio=='vpn':
                status = getoutput(f"sudo systemctl start VpnKyoBot.service -p SubState")
            elif servizio=='ssh':
                status = getoutput(f"sudo systemctl start sshd -p SubState")
            return 'avviato'
            
    if azione=='stop':
        if stato_servizio=='dead':
            print ( 'Servizio ',servizio,'già Stoppato')
            return 'già Stoppato'
        else:
            print ('Stoppo il servizio ',servizio)
            if servizio=='vpn':
                status = getoutput(f"sudo systemctl stop VpnKyoBot.service -p SubState")
            elif servizio=='ssh':
                status = getoutput(f"sudo systemctl stop sshd -p SubState")
            return 'stoppato'
def getCPUtemperature():
    res = os.popen('vcgencmd measure_temp').readline()
    return(res.replace("temp=","").replace("'C\n",""))
def getDiskSpace():
    p = os.popen("df -h /")
    i = 0
    while 1:
        i = i +1
        line = p.readline()
        if i==2:
            return(line.split()[1:5])
def stato_hw(cb):
    
    uname = platform.uname()
    hostname=uname.node
    
    temp_cpu=getCPUtemperature()
    
    load1, load5, load15 = psutil.getloadavg()
    cpu_usage_1 =   round((load1/os.cpu_count()) * 100,3)
    cpu_usage_5 =   round((load5/os.cpu_count()) * 100,3)
    cpu_usage_15 =  round((load15/os.cpu_count()) * 100,3)
    
    svmem = psutil.virtual_memory()
    RAM_totale=get_size(svmem.total)
    RAM_disponibile =get_size(svmem.available)
    RAM_usata =get_size(svmem.used)
    RAM_perc =svmem.percent
 
    DISK_stats = getDiskSpace()
    DISK_totale = DISK_stats[0]
    DISK_usato = DISK_stats[1]
    DISK_perc = DISK_stats[3]
    
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.fromtimestamp(boot_time_timestamp)
    
    dt = datetime.now()
    
    info =  f"Ecco le tue informazioni del tuo Hardware :\n" \
            f"<pre>\n" \
            f"Hostname            : {hostname}\n" \
            f"---------------------\n"\
            f"Temperatura Cpu     : {temp_cpu}°\n" \
            f"---------------------\n"\
            f"CPU Media 1 Minuto  : {cpu_usage_1} %\n"\
            f"CPU Media 5 Minuti  : {cpu_usage_5} %\n"\
            f"CPU Media 15 Minuti : {cpu_usage_15} %\n"\
            f"---------------------\n"\
            f"RAM Totale          : {RAM_totale}\n"\
            f"RAM Disponibile     : {RAM_disponibile}\n"\
            f"RAM Usata           : {RAM_usata}\n"\
            f"RAM Usata %         : {RAM_perc} %\n"\
            f"---------------------\n"\
            f"DISCO Totale        : {DISK_totale}\n"\
            f"DISCO Usato         : {DISK_usato}\n"\
            f"DISCO Usato %       : {DISK_perc}\n"\
            f"---------------------\n"\
            f"Ultimo Riavvio      : {bt.day}/{bt.month}/{bt.year} {bt.hour}:{bt.minute}:{bt.second}\n"\
            f"Data e ora          : {dt.day}/{dt.month}/{dt.year} {dt.hour}:{dt.minute}:{dt.second}\n"\
            f"</pre>\n" 
    bot.send_message(cb.message.chat.id, info,parse_mode='html' )
def stato_net(cb):
    if_addrs = psutil.net_if_addrs()
    info_net=f"Ecco le tue informazioni della tua Rete :\n"
    info_net+=f"<pre>\n"
    for interface_name, interface_addresses in if_addrs.items():
        for address in interface_addresses:
            if str(address.family) == 'AddressFamily.AF_INET':
                if interface_name=='lo':break
                info_net+=f" Interfaccia: {interface_name} \n"
                info_net+=f" IP Address : {address.address}\n"
                info_net+=f" Netmask    : {address.netmask}\n"
            elif str(address.family) == 'AddressFamily.AF_PACKET':
                info_net+=f" MAC Address: {address.address}\n\n"
    info_net+='</pre>'
    bot.send_message(cb.message.chat.id, info_net,parse_mode='html' )

# Leggo il Json degli utenti
def leggi_json():
    file_json = open('users.json')
    #global membri
    membri=[]
    try:
        membri=json.load(file_json)
    except:
        print('json vuoto')
    return membri
 
def leggi_log(n):
    file_log = open('log.txt',"r")
    lines=file_log.readlines()
    last_lines=''
    for i in range(1,n):
        last_lines=lines[i*-1]+'\n'+last_lines
    
    last_lines='<pre>\n'+last_lines+'</pre>\n'        
    return last_lines
    
def leggi_stati(resp):
    # qui leggo gli stati ...
    stato_area1     =   True if GPIO.input(pin_oc1) ==0  else False
    stato_area2     =   True if GPIO.input(pin_oc2) ==0  else False
    stato_allarme   =   True if GPIO.input(pin_no)  ==0  else False
    stato_guasti    =   True if GPIO.input(pin_oc3) ==0  else False
    stato_z1        =   True if GPIO.input(pin_z1)  ==0  else False
    stato_z2        =   True if GPIO.input(pin_z2)  ==0  else False
    stato_z3        =   True if GPIO.input(pin_z3)  ==0  else False
    stato_z4        =   True if GPIO.input(pin_z4)  ==0  else False
    stato_z5        =   True if GPIO.input(pin_z5)  ==0  else False
    stato_z6        =   True if GPIO.input(pin_z6)  ==0  else False
    
    cfgjsn=leggi_config()
    stato_smart     =   cfgjsn['Smart']
        
    dati={'area1'   :stato_area1    ,\
          'area2'   :stato_area2    ,\
          'allarme' :stato_allarme  ,\
          'guasti'  :stato_guasti   ,\
          'z1'      :stato_z1       ,\
          'z2'      :stato_z2       ,\
          'z3'      :stato_z3       ,\
          'z4'      :stato_z4       ,\
          'z5'      :stato_z5       ,\
          'z6'      :stato_z6       ,\
          'smart'   :stato_smart    }
    
    stati = json.dumps(dati)
    
    # qui definisco i led ...
    led_area1   = '🟢 ' if stato_area1   == False else '🔴 '
    led_area2   = '🟢 ' if stato_area2   == False else '🔴 '
    led_allarme = '🟢 ' if stato_allarme == False else '🔴 '
    led_guasti  = '🟢 ' if stato_guasti  == False else '🔴 '
    led_z1      = '🟢 ' if stato_z1      == False else '🔴 '
    led_z2      = '🟢 ' if stato_z2      == False else '🔴 '
    led_z3      = '🟢 ' if stato_z3      == False else '🔴 '
    led_z4      = '🟢 ' if stato_z4      == False else '🔴 '
    led_z5      = '🟢 ' if stato_z5      == False else '🔴 '
    led_z6      = '🟢 ' if stato_z6      == False else '🔴 '
    led_smart   = '🟢 ' if stato_smart   == 'False' else '🔴 '
    dati={'area1'   :led_area1  ,\
          'area2'   :led_area2  ,\
          'allarme' :led_allarme,\
          'guasti'  :led_guasti ,\
          'z1'      :led_z1     ,\
          'z2'      :led_z2     ,\
          'z3'      :led_z3     ,\
          'z4'      :led_z4     ,\
          'z5'      :led_z5     ,\
          'z6'      :led_z6     ,\
          'smart'   :led_smart  }
    leds= json.dumps(dati)
    if resp=="leds":
        return leds
    else:
        return stati
    
def keyboard_admin():
    # definisco la tastiera di default
    markup = types.ReplyKeyboardMarkup(row_width=3,resize_keyboard=True)
    itembtn1 = types.KeyboardButton('Stato')
    itembtn2 = types.KeyboardButton('Inserisci')
    itembtn3 = types.KeyboardButton('Disinserisci')
    itembtn4 = types.KeyboardButton('Istruzioni')
    itembtn5 = types.KeyboardButton('Info')
    itembtn6 = types.KeyboardButton('⚙️ Admin ⚙️')
    markup.add(itembtn1, itembtn2, itembtn3, itembtn4, itembtn5, itembtn6)
    return markup

def scrivi_json(id,dato,valore):
    print ('scrivo il json degli users ...')
    try:
        in_file = open('users.json', 'r')
        data_file = in_file.read()
        data = json.loads(data_file)
        
        for utente in data:
            if utente['id']==id:
                utente[dato]=valore
                break
            
        out_file = open('users.json','w')
        out_file.write(json.dumps(data,indent=4))
        out_file.close()
        leggi_json()
        
        
        return True
    except Exception as e:
        print (e)
        return e

def elimina_utente(id):
    try:
        in_file = open('users.json', 'r')
        data_file = in_file.read()
        data = json.loads(data_file)
        
        for idx,obj in enumerate(data):
            if obj['id']==id:
                data.pop(idx)
                break
        
        out_file = open('users.json','w')
        out_file.write(json.dumps(data,indent=4))
        out_file.close()
        leggi_json()
        
        
        return True
    except Exception as e:
        print (e)
        return e

def is_administrator(id):
    membri=leggi_json()
    for membro in membri:
        #print('Admins -> ',membro['id'])
        if id==int(membro['id']) and membro['admin']=='True':
            return True
            break
          
def is_member(id):
    # Rileggi il file degli utenti
    global membri
    membri=leggi_json()
    for membro in membri:
        if id==int(membro['id']) :
            return True
            break

def autorizzazioni(id,comando):
    if is_member(id)!=True:
        bot.send_message(id, 'NON puoi gestire l\'allarme.\nElimina la Chat e richiedi nuovamente il consenso al Proprietario')
        
    led=json.loads(leggi_stati('leds'))
    btn1    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn2    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn3    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn4    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn5    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn6    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn7    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn8    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn9    = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn10   = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    btn11   = types.InlineKeyboardButton('🚫',callback_data="cb_funz_vietata")
    for membro in membri:
        if comando == 'inserisci':
            if id==int(membro['id']) and membro['ins_area1']=='True':
                btn1 = types.InlineKeyboardButton(led['area1']+cfgjsn['Area1'],callback_data="cb_ins_area1")
            if id==int(membro['id']) and membro['ins_area2']=='True':
                btn2 = types.InlineKeyboardButton(led['area2']+cfgjsn['Area2'],callback_data="cb_ins_area2")
            if id==int(membro['id']) and membro['ins_totale']=='True':
                btn3 = types.InlineKeyboardButton('Totale',callback_data="cb_ins_totale")
            if id==int(membro['id']) and membro['ins_smart']=='True':
                btn4 = types.InlineKeyboardButton(led['smart']+'Smart',callback_data="cb_ins_smart")
            
        elif comando == 'disinserisci':
            if id==int(membro['id']) and membro['dis_area1']=='True':
                btn1 = types.InlineKeyboardButton(led['area1']+cfgjsn['Area1'],callback_data="cb_dis_area1")
            if id==int(membro['id']) and membro['dis_area2']=='True':
                btn2 = types.InlineKeyboardButton(led['area2']+cfgjsn['Area2'],callback_data="cb_dis_area2")
            if id==int(membro['id']) and membro['dis_totale']=='True':
                btn3 = types.InlineKeyboardButton('Totale',callback_data="cb_dis_totale") 
            if id==int(membro['id']) and membro['dis_smart']=='True':
                btn4 = types.InlineKeyboardButton(led['smart']+'Smart',callback_data="cb_dis_smart")
        
        elif comando == 'stato':
            if id==int(membro['id']) and membro['stato_area1']=='True':
                btn1 = types.InlineKeyboardButton(led['area1']+cfgjsn['Area1'],callback_data="cb_stato")
            if id==int(membro['id']) and membro['stato_area2']=='True':
               btn2 = types.InlineKeyboardButton(led['area2']+cfgjsn['Area2'],callback_data="cb_stato")
            if id==int(membro['id']) and membro['stato_guasti']=='True':
                btn3 = types.InlineKeyboardButton(led['guasti']+'Guasti',callback_data="cb_stato")
            if id==int(membro['id']) and membro['stato_allarme']=='True':    
                btn4 = types.InlineKeyboardButton(led['allarme']+'Allarme',callback_data="cb_stato")  
            if id==int(membro['id']) and membro['stato_z1']=='True':   
                btn5 = types.InlineKeyboardButton(led['z1']+cfgjsn['Zona1'],callback_data="cb_stato")  
            if id==int(membro['id']) and membro['stato_z2']=='True':    
                btn6 = types.InlineKeyboardButton(led['z2']+cfgjsn['Zona2'],callback_data="cb_stato")  
            if id==int(membro['id']) and membro['stato_z3']=='True':    
                btn7 = types.InlineKeyboardButton(led['z3']+cfgjsn['Zona3'],callback_data="cb_stato")  
            if id==int(membro['id']) and membro['stato_z4']=='True':    
                btn8 = types.InlineKeyboardButton(led['z4']+cfgjsn['Zona4'],callback_data="cb_stato")  
            if id==int(membro['id']) and membro['stato_z5']=='True':    
                btn9 = types.InlineKeyboardButton(led['z5']+cfgjsn['Zona5'],callback_data="cb_stato")  
            if id==int(membro['id']) and membro['stato_z6']=='True':    
                btn10 = types.InlineKeyboardButton(led['z6']+cfgjsn['Zona6'],callback_data="cb_stato")  
            if id==int(membro['id']) and membro['stato_smart']=='True':
               btn11 = types.InlineKeyboardButton(led['smart']+'Smart',callback_data="cb_stato")
            
    return btn1,btn2,btn3,btn4,btn5,btn6,btn7,btn8,btn9,btn10 ,btn11       
               
def find_owner():
    for membro in membri:
        #print('Admins -> ',membro['id'])
        if  membro['owner']=='True':
            id=int(membro['id'])
            return [id,membro['nome']]
            break  
  
def add_user(message):
    # aggiungi l'utente
    membri.append({ 'id':message.from_user.id,
                    'nome':message.from_user.first_name,
                    'cognome':message.from_user.last_name,
                    'admin':'False',
                    'owner':'False',
                    'ins_area1':"False",
                    'ins_area2':"False",
                    'ins_area2':"False",
                    'ins_totale':"False",
                    'ins_smart':"False",
                    'dis_area1':"False",
                    'dis_area2':"False",
                    'dis_totale':"False",
                    'dis_smart':"False",
                    'stato_area1':"False",
                    'stato_area2':"False",
                    'stato_smart':"False",
                    'stato_allarme':"False",
                    'stato_sirena':"False",
                    "stato_guasti": "False",
                    "stato_z1": "False",
                    "stato_z2": "False",
                    "stato_z3": "False",
                    "stato_z4": "False",
                    "stato_z5": "False",
                    "stato_z6": "False",
                    "auto_ins": "False",
                    "video_ver": "False"
                    })
    
    with open("users.json", "w") as jsonFile:
        json.dump(membri,jsonFile,indent=4)
        return True

def istruzioni(message):
    print('Istruzioni...')
    #print(message)
    
    istr_user = f"Con l\'uso di questo BOT puoi gestire la tua centrale d\'allarme Kyo.\n"          \
                f"Nel menu sottostante trovi i seguenti tasti:\n\n"                                 \
                f"\"<b>Stato</b>\" : Ti permette di leggere lo stato della centrale\n"                   \
                f"\"<b>Inserisci</b>\": Ti permette di Inserire l\'allarme Normale o Smart \n"         \
                f"\"<b>Disinserisci</b>\": Ti permette di Disinserire l\'allarme Normale o Smart \n"   \
                f"\"<b>Info</b>\" : Ti mostra le tue informazioni Telegram \n"                           \
                f"\"<b>Admin</b>\" : Sezione dedicata all'amministratore dell\'Allarme.\n\n"               \
                f"Ricordati inoltre i seguenti simboli:\n\n"                                        \
                f"🟢 = <b>Area o Zona Disinserita</b>\n"\
                f"🟢 = <b>Nessun Allarme o Guasto in corso</b>\n\n"\
                f"🔴 = <b>Area o Zona Inserita</b>\n"\
                f"🔴 = <b>Allarme o Guasto in corso</b>\n\n"\
                f"Se il menu in basso sparisce , lo puoi richiamre inviando un messaggio con scritto \"<b>menu</b>\"\n\n\n"\
                f"<i>In teoria non puoi scrivere messaggi al bot ...\n"\
                f"ma se trovi le \"<b>parole giuste</b>\" potrebbe risponderti a modo... </i>\n\n\n"
                
    istr_admin= f"La Sezione \"Admin\" ti permette di avere i seguenti servizi:\n\n"\
                f"- \"<b>Leggi Log</b>\" : Leggi i log di sistema\n"\
                f"- \"<b>Lista Utenti</b>\" : Vedi gli utenti e i loro permessi\n"\
                f"- \"<b>Gestisci Permessi</b>\" : Assegni permessi agli utenti\n"\
                f"- \"<b>Gestione Nomi</b>\" : Assegni i nomi alle Aree e alle Zone\n"\
                f"- \"<b>Gestione Servizi</b>\" : Avvii o Stoppi i seguenti servizi\n"\
                    f"     - \"<b>Vpn</b>\" : Accesso Remoto per Telegestione\n"\
                    f"     - \"<b>Ssh</b>\" : Accesso locale/remoto console ssh\n"\
                    f"     - \"<b>KyoBot</b>\" : Questo bot\n"\
                f"- \"<b>Stato HW</b>\" : Mostra lo stato dell\'harware\n"\
                f"- \"<b>Stato Rete</b>\" : Mostra lo stato della rete\n"\
                f"- \"<b>Funzioni Smart</b>\" : Configuri le seguenti Funzioni\n"\
                    f"     - \"<b>Auto Inserimento</b>\" : Ti suggerisce di inserire l\'Allarme se nessuno è in casa.\n"\
                    f"     - \"<b>Video Verifica</b>\" : Allega il video di una o piu telecamere/webcam quando scatta l\'Allarme.\n"\
    
    if(is_administrator(message.chat.id)==True):
        istruzioni=istr_user+istr_admin
    else:
        istruzioni=istr_user
    bot.send_message(message.chat.id, istruzioni,parse_mode='html')
    
def menu_inserisci(message):
    print('Menu Inserisci...')
    btn = autorizzazioni(message.chat.id,'inserisci')    
    markup_ins = types.InlineKeyboardMarkup()
    markup_ins.add(btn[0],btn[1])
    markup_ins.add(btn[2])
    markup_ins.add(btn[3]) 
    bot.send_message(message.chat.id, "Quale Area vuoi inserire ?", reply_markup=markup_ins)

def menu_disinserisci(message):
    print('Menu Disinserisci...')
    btn = autorizzazioni(message.chat.id,'disinserisci')
    markup_dis = types.InlineKeyboardMarkup()
    markup_dis.add(btn[0],btn[1])
    markup_dis.add(btn[2])
    markup_dis.add(btn[3])   
    bot.send_message(message.chat.id, "Quale Area vuoi Disinserire ?", reply_markup=markup_dis)

def info(message):
    id=message.from_user.id
    nome=message.from_user.first_name
    if message.from_user.last_name  :
        cognome=message.from_user.last_name
    else:
        cognome=''
    if message.from_user.username  :
        username=message.from_user.username
    else:
        username=''
    info="Ecco le tue informazioni Telegram :\n\
Nome : "+nome+"\n\n\
Cognome : "+cognome+"\n\n\
Username : "+username+"\n\n\
ID : "+str(id)

    info =  f"Ecco le tue informazioni Telegram :\n" \
            f"<pre>\n" \
            f"ID        : {str(id)}\n" \
            f"Nome      : {nome}\n" \
            f"Cognome   : {cognome}\n"\
            f"Username  : {username}\n"\
            f"</pre>\n" 
    bot.send_message(message.chat.id, info,parse_mode='html')

def menu_admin(message):
    print('Menu Admin...')
    if(is_administrator(message.chat.id)==True):
        btn1 =  types.InlineKeyboardButton('Leggi Log'           ,callback_data="cb_leggi_log")
        btn2 =  types.InlineKeyboardButton('Lista Utenti'        ,callback_data="cb_lista_utenti")
        btn3 =  types.InlineKeyboardButton('Gestisci Permessi'   ,callback_data="cb_gest_permessi")
        btn4 =  types.InlineKeyboardButton('Gestione Nomi'       ,callback_data="cb_gest_nomi")
        btn5 =  types.InlineKeyboardButton('Gestione Servizi'    ,callback_data="cb_gest_servizi")        
        btn6 =  types.InlineKeyboardButton('Stato HW'            ,callback_data="cb_stato_hw")
        btn7 =  types.InlineKeyboardButton('Stato Rete'          ,callback_data="cb_stato_net")
        #btn8 =  types.InlineKeyboardButton('Video WebCam'        ,callback_data="cb_video_webcam")
        #btn9 =  types.InlineKeyboardButton('Video Stream'        ,callback_data="cb_video_stream")
        btn8 = types.InlineKeyboardButton('Funzioni Smart'      ,callback_data="cb_funzioni_smart")
        
        markup_admin = types.InlineKeyboardMarkup(row_width=3)
        markup_admin.add(btn1,btn2,btn3,btn4,btn5,btn6,btn7,btn8) 
        bot.send_message(message.chat.id,"<b>Scegli un\'opzione...</b>", reply_markup=markup_admin,parse_mode='html')
    else:
        bot.send_message(message.chat.id,message.from_user.first_name+" NON Sei un Amministratore.\nSe vuoi i diritti di Amministratore chiedi al proprietario.")
    
def menu_smart(cb):
    print('Menu Smart...')
    cb.from_user.first_name
    if(is_administrator(cb.from_user.id)==True):
        btn1 =  types.InlineKeyboardButton('Auto Inserimento'                   ,callback_data="cb_smart_ai")
        btn2 =  types.InlineKeyboardButton('Video Verifica'                     ,callback_data="cb_smart_video_ver")
        
        
        markup_smart = types.InlineKeyboardMarkup(row_width=1)
        markup_smart.add(btn1,btn2) 
        bot.send_message(cb.message.chat.id,"<b>Quale Funzione vuoi Gestire ?</b>", reply_markup=markup_smart,parse_mode='html')
    else:
        bot.send_message(cb.message.chat.id,cb.from_user.first_name+" NON Sei un Amministratore.\nSe vuoi i diritti di Amministratore chiedi al proprietario.")

def menu_smart_ai(cb):
    print('Menu Smart ai...')
    
    btn_abilita =  types.InlineKeyboardButton       ('Abilita/Disabilita',callback_data="cb_smart_ai_abilita")
    btn_timer =  types.InlineKeyboardButton         ('Tempo Inattività'  ,callback_data="cb_smart_ai_timer")
    btn_fascia_oraria =  types.InlineKeyboardButton ('Fascia Oraria'     ,callback_data="cb_smart_ai_fo")
    btn_back =  types.InlineKeyboardButton          ('⬅'                 ,callback_data="cb_smart_ai_back")
    
    markup_smart_ai = types.InlineKeyboardMarkup(row_width=1)
    markup_smart_ai.add(btn_abilita,btn_timer,btn_fascia_oraria,btn_back) 
    bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id,
                          text='Scegli l\'opzione da modificare',reply_markup=markup_smart_ai ,parse_mode='html')
def menu_smart_ai_abilita(cb):
    print('Menu Smart ai abilita/disabilita...')
    cfgjsn=leggi_config()
    
    btn_si_disattiva =  types.InlineKeyboardButton  ('SI',callback_data="cb_smart_ai_disattiva")
    btn_si_attiva =  types.InlineKeyboardButton     ('SI',callback_data="cb_smart_ai_attiva")
    btn_no =  types.InlineKeyboardButton            ('NO',callback_data="cb_smart_ai_NO")
    btn_back =  types.InlineKeyboardButton          ('⬅' ,callback_data="cb_smart_ai_back")
    
    markup_smart_ai = types.InlineKeyboardMarkup(row_width=2)
    
    if cfgjsn['Auto_Ins']=='True':
        markup_smart_ai.add(btn_si_disattiva,btn_no) 
        markup_smart_ai.add(btn_back)
        bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id,
                          text='Lo stato del Servizio \"<b>Auto Inserimento</b> \" è : \n <b>Attivo</b>.\n Lo vuoi Disattivare ?',reply_markup=markup_smart_ai ,parse_mode='html')

    else:
        markup_smart_ai.add(btn_si_attiva,btn_no) 
        markup_smart_ai.add(btn_back)
        bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id,
                          text='Lo stato del Servizio \"<b>Auto Inserimento</b> \" è : \n <b>Disattivo</b>.\n Lo vuoi Attivare ?',reply_markup=markup_smart_ai ,parse_mode='html')
def menu_smart_ai_timer(cb):
    print('Menu Smart ai Timer...')
    cfgjsn=leggi_config()
    markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il tempo di inattività dei sensori ( espresso in minuti )')
    msg=bot.send_message(cb.message.chat.id,'Il tempo di inattività attualmente è di '+cfgjsn['Timer_a_i']+' minuti.\nInserisci il nuovo valore espresso in minuti...' ,parse_mode='html',reply_markup=markup_force_reply,)
    bot.register_next_step_handler(msg, menu_smart_ai_cambio_timer) 
def menu_smart_ai_cambio_timer(message):
    chat_id = message.chat.id
    timer_new = message.text
    nome=message.from_user.first_name
    if timer_new.isnumeric()==False:
        bot.send_message(chat_id,'Puoi inserire solo valori numerici...',reply_markup=keyboard_admin())
        return
    try:
        in_file = open('config.json', 'r')
        data_file = in_file.read()
        data = json.loads(data_file)
        data["Timer_a_i"] = timer_new
        out_file = open('config.json','w')
        out_file.write(json.dumps(data,indent=4))
        out_file.close()
        global cfgjsn   
        cfgjsn=leggi_config()
        log(nome + ' ha cambiato il tempo dell\' Auto Inserimento in '+timer_new+' minuti.' )
        
        bot.send_message(chat_id,'Ho Modificato il tempo di inattività dei sensori in '+timer_new+' minuti.',reply_markup=keyboard_admin())
    except Exception as e:
        print (e)
        bot.reply_to(message, "oooops c'è stato un errore nello scrivere il file di configurazione",reply_markup=keyboard_admin())
def menu_smart_ai_fascia_oraria(cb):
    print('Menu Smart ai Fascia Oraria...')
    cfgjsn=leggi_config()
    testo=  f"Attualmente la funzione di \"Auto Inserimento\" "\
            f"è attiva dalle {cfgjsn['Start_a_i']} alle {cfgjsn['Stop_a_i']}\n"
    bot.send_message(cb.message.chat.id,testo,parse_mode='html')
    markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci l\'ora di inizio della funzione di \"Auto Inserimento\"')
    msg=bot.send_message(cb.message.chat.id,'Inserisci <b>l\'ora di inizio</b> della funzione di \"Auto Inserimento\"',parse_mode='html',reply_markup=markup_force_reply)
    bot.register_next_step_handler(msg, menu_smart_ai_cambio_fo,'inizio') 
def menu_smart_ai_cambio_fo(message,tipo):
    chat_id = message.chat.id
    valore_new = message.text
    nome=message.from_user.first_name
    if valore_new.isnumeric()==False:
        bot.send_message(chat_id,'Puoi inserire solo valori numerici...',reply_markup=keyboard_admin())
        return 
    if tipo=='inizio':
        dato="Start_a_i"
        dato_log='Inizio'
        txt_resp='La funzione \"Auto Inserimento \" partirà dalle ore :'+valore_new
    elif tipo=='fine':
        dato="Stop_a_i"
        dato_log='Fine'
        txt_resp='La funzione \"Auto Inserimento \" terminerà dalle ore :'+valore_new
    try:
        in_file = open('config.json', 'r')
        data_file = in_file.read()
        data = json.loads(data_file)
        data[dato] = valore_new
        out_file = open('config.json','w')
        out_file.write(json.dumps(data,indent=4))
        out_file.close()
        global cfgjsn   
        cfgjsn=leggi_config()
        
        log(nome + ' ha cambiato il valore di '+dato_log + '  dell\' Auto Inserimento alle ore  '+valore_new+'.' )
        
        
        bot.send_message(chat_id,txt_resp,reply_markup=keyboard_admin())
        
        if tipo=='fine':
            return
        
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci l\'ora di inizio della funzione di \"Auto Inserimento\"')
        msg=bot.send_message(chat_id,'Inserisci <b>l\'ora di Fine</b> della funzione di \"Auto Inserimento\"',parse_mode='html',reply_markup=markup_force_reply)
        bot.register_next_step_handler(msg, menu_smart_ai_cambio_fo,'fine')
        
    except Exception as e:
        print (e)
        bot.reply_to(message, "oooops c'è stato un errore nello scrivere il file di configurazione",reply_markup=keyboard_admin())
     
def menu_smart_video_ver(cb):
    print ('Menu Smart Video Verifica')
    btn_abilita =  types.InlineKeyboardButton('Abilita/Disabilita'  ,callback_data="cb_smart_vv_abilita")
    btn_link =  types.InlineKeyboardButton   ('Imposta Link'        ,callback_data="cb_smart_vv_link")
    
    markup_smart_vv = types.InlineKeyboardMarkup(row_width=1)
    markup_smart_vv.add(btn_abilita,btn_link) 
    bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id,
                          text='Scegli l\'opzione da modificare',reply_markup=markup_smart_vv ,parse_mode='html')
def menu_smart_video_ver_abilita(cb):
    print ('Menu Smart Video Verifica Abilita/Disabilita')
    cfgjsn=leggi_config()
    
    btn_si_disattiva =  types.InlineKeyboardButton  ('SI',callback_data="cb_smart_vv_disattiva")
    btn_si_attiva =  types.InlineKeyboardButton     ('SI',callback_data="cb_smart_vv_attiva")
    btn_no =  types.InlineKeyboardButton            ('NO',callback_data="cb_smart_vv_NO")
    btn_back =  types.InlineKeyboardButton          ('⬅' ,callback_data="cb_smart_vv_back")
    
    markup_smart_vv = types.InlineKeyboardMarkup(row_width=2)
    
    if cfgjsn['Video']=='True':
        markup_smart_vv.add(btn_si_disattiva,btn_no) 
        markup_smart_vv.add(btn_back)
        bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id,
                          text='Lo stato del Servizio \"<b>Video Verifica</b> \" è : \n <b>Attivo</b>.\n Lo vuoi Disattivare ?',reply_markup=markup_smart_vv ,parse_mode='html')

    else:
        markup_smart_vv.add(btn_si_attiva,btn_no) 
        markup_smart_vv.add(btn_back)
        bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id,
                          text='Lo stato del Servizio \"<b>Video Verifica</b> \" è : \n <b>Disattivo</b>.\n Lo vuoi Attivare ?',reply_markup=markup_smart_vv ,parse_mode='html')
def menu_smart_vv_link(cb):
    print('menu_smart_vv_link')
    cfgjsn=leggi_config()
    btn_1 =  types.InlineKeyboardButton('Video Zona 1'  ,callback_data="cb_smart_vv_link_1")
    btn_2 =  types.InlineKeyboardButton('Video Zona 2'  ,callback_data="cb_smart_vv_link_2")
    btn_3 =  types.InlineKeyboardButton('Video Zona 3'  ,callback_data="cb_smart_vv_link_3")
    btn_4 =  types.InlineKeyboardButton('Video Zona 4'  ,callback_data="cb_smart_vv_link_4")
    btn_5 =  types.InlineKeyboardButton('Video Zona 5'  ,callback_data="cb_smart_vv_link_5")
    btn_6 =  types.InlineKeyboardButton('Video Zona 6'  ,callback_data="cb_smart_vv_link_6")
    
    markup_smart_vv_link = types.InlineKeyboardMarkup(row_width=1)
    markup_smart_vv_link.add(btn_1,btn_2,btn_3,btn_4,btn_5,btn_6) 
    bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id,
                          text='Scegli la Zona da modificare',reply_markup=markup_smart_vv_link ,parse_mode='html')
def menu_smart_vv_link_Z(cb,zona):
    print('menu_smart_vv_link_Z'+str(zona))
    cfgjsn=leggi_config()
    link=cfgjsn['Video'+str(zona)]
    markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il nuovo link')
    
    msg=bot.send_message(  chat_id=cb.message.chat.id,
                            text='Il Link Video della \"<b>Zona'+str(zona) +'</b> \" è : \n <b>'+link +'</b>.\n Inserisci il nuovo Link',
                            reply_markup=markup_force_reply ,
                            parse_mode='html')
    bot.register_next_step_handler(msg, menu_smart_vv_cambio_link,zona)
def menu_smart_vv_cambio_link(message,zona):
    print ('menu_smart_vv_cambio_link zona '+str(zona))
    chat_id = message.chat.id
    link_new = message.text
    video='Video'+str(zona)
    nome=message.from_user.first_name
    try:
        in_file = open('config.json', 'r')
        data_file = in_file.read()
        data = json.loads(data_file)
        data[video] = link_new
        out_file = open('config.json','w')
        out_file.write(json.dumps(data,indent=4))
        out_file.close()
        global cfgjsn   
        cfgjsn=leggi_config()
        log(nome + ' ha modificato il link della Zona'+str(zona)+' in '+link_new)
        
        
        bot.send_message(chat_id,'Ho Modificato il link video della Zona '+str(zona)+'  in <b>'+link_new+'</b>.',reply_markup=keyboard_admin(),parse_mode='html')
    except Exception as e:
        print (e)
        bot.reply_to(message, "oooops c'è stato un errore nello scrivere il file di configurazione",reply_markup=keyboard_admin())


def inserisci(area,message):
    print('inserisci...')
    
    # leggi lo stato della centrale
    stati=json.loads(leggi_stati('stati'))
        
    
    markup_ins = types.InlineKeyboardMarkup()
    btn2 = types.InlineKeyboardButton('NO',callback_data="cb_ins_NO")

    if(area=='Area1'):
        if stati['area1']==True:
          bot.send_message(message.chat.id, cfgjsn['Area1']+ " è già inserito") 
        else: 
            btn1 = types.InlineKeyboardButton('SI',callback_data="cb_ins_A1_SI") 
            markup_ins.add(btn1,btn2)  
            bot.send_message(message.chat.id, "Sei Sicuro di voler inserire "+cfgjsn['Area1']+" ?", reply_markup=markup_ins)
    elif(area=='Area2'):
        if stati['area2']==True:
          bot.send_message(message.chat.id, cfgjsn['Area2']+"  è già inserito") 
        else:
            btn1 = types.InlineKeyboardButton('SI',callback_data="cb_ins_A2_SI")
            markup_ins.add(btn1,btn2)  
            bot.send_message(message.chat.id, "Sei Sicuro di voler inserire "+cfgjsn['Area2']+" ?", reply_markup=markup_ins)
    elif (area=='Totale'):
            btn1 = types.InlineKeyboardButton('SI',callback_data="cb_ins_Tot_SI")
            markup_ins.add(btn1,btn2)  
            bot.send_message(message.chat.id, "Sei Sicuro di voler inserire il Totale ?", reply_markup=markup_ins)
    
    elif(area=='Smart'):
        btn1 = types.InlineKeyboardButton('SI',callback_data="cb_ins_S_SI")
        markup_ins.add(btn1,btn2)  
        bot.send_message(message.chat.id, "Sei Sicuro di voler inserire l\'<b>Allarme Smart</b> ?", reply_markup=markup_ins,parse_mode='html')
    
def disinserisci(area,message):
    print('Disinserisci...')
    
    # leggi lo stato della centrale
    stati=json.loads(leggi_stati('stati'))
        
    
    markup_ins = types.InlineKeyboardMarkup()
    btn2 = types.InlineKeyboardButton('NO',callback_data="cb_dis_NO")

    if(area=='Area1'):
        if stati['area1']==False:
          bot.send_message(message.chat.id, cfgjsn['Area1']+" è già Disinserito") 
        else: 
            btn1 = types.InlineKeyboardButton('SI',callback_data="cb_dis_A1_SI") 
            markup_ins.add(btn1,btn2)  
            bot.send_message(message.chat.id, "Sei Sicuro di voler Disinserire "+cfgjsn['Area1']+" ?", reply_markup=markup_ins)
    elif(area=='Area2'):
        if stati['area2']==False:
          bot.send_message(message.chat.id, "L'Area2  è già Disinserita") 
        else:
            btn1 = types.InlineKeyboardButton('SI',callback_data="cb_dis_A2_SI")
            markup_ins.add(btn1,btn2)  
            bot.send_message(message.chat.id, "Sei Sicuro di voler Disinserire l'Area2 ?", reply_markup=markup_ins)
    elif (area=='Totale'):
            btn1 = types.InlineKeyboardButton('SI',callback_data="cb_dis_Tot_SI")
            markup_ins.add(btn1,btn2)  
            bot.send_message(message.chat.id, "Sei Sicuro di voler Disinserire il Totale ?", reply_markup=markup_ins)
    
    elif(area=='Smart'):
        btn1 = types.InlineKeyboardButton('SI',callback_data="cb_dis_S_SI")
        markup_ins.add(btn1,btn2)  
        bot.send_message(message.chat.id, "Sei Sicuro di voler Disinserire l\'<b>Allarme Smart</b> ?", reply_markup=markup_ins,parse_mode='html')
 
def menu_stato(id):
    print('Menu Stato...')
    utente=leggi_utente(id)
    log (utente['nome']+' ha visualizzato lo Stato dell\' impianto')
    btn = autorizzazioni(id,'stato')
    markup_stato = types.InlineKeyboardMarkup(row_width=3)
    markup_stato.add(btn[3],btn[2]) 
    markup_stato.add(btn[0],btn[1])
    markup_stato.add(btn[10])
    markup_stato.add(btn[4],btn[5],btn[6])
    markup_stato.add(btn[7],btn[8],btn[9])
    
    bot.send_message(id, "Ecco lo stato del tuo impianto...", reply_markup=markup_stato)

def menu_not_member(message):
    markup_nm = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('SI',callback_data="not_member_SI")
    btn2 = types.InlineKeyboardButton('NO',callback_data="not_member_NO")
    markup_nm.add(btn1,btn2) 
    bot.send_message(message.chat.id,  message.from_user.first_name+' NON sei autorizzato a gestire l\'allarme.\n\n\
Vuoi chiedere l\'autorizzazione al proprietario?',reply_markup=markup_nm)
        
def not_member(cb):
    id_owner=find_owner()[0]
    nome_owner=find_owner()[1]
    markup_nm_add = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Certo',callback_data="add_not_member_SI")
    btn2 = types.InlineKeyboardButton('Assolutamente NO',callback_data="add_not_member_NO")
    markup_nm_add.add(btn1,btn2)
    bot.send_message(id_owner, "Ciao "+nome_owner+" \n"+cb.from_user.first_name+" vorrebbe gestire l\'allarme.\nSei d\'accordo ?", reply_markup=markup_nm_add) 
    log(cb.from_user.first_name+" Ha chiesto di poter gestire l\'allarme")    

def leggi_utente(id):
    #print ('Leggi Utente ',id)
    utenti=leggi_json()
    for utente in utenti:
        if utente['id']==id:
            return utente
            break

def gest_nomi(message):
    print ('Gestione Nomi ...') 
    btn1 = types.InlineKeyboardButton('Area1',callback_data="cb_gest_nomi_Area1")
    btn2 = types.InlineKeyboardButton('Area2',callback_data="cb_gest_nomi_Area2")
    btn3 = types.InlineKeyboardButton('Zona1',callback_data="cb_gest_nomi_Zona1")
    btn4 = types.InlineKeyboardButton('Zona2',callback_data="cb_gest_nomi_Zona2")
    btn5 = types.InlineKeyboardButton('Zona3',callback_data="cb_gest_nomi_Zona3")
    btn6 = types.InlineKeyboardButton('Zona4',callback_data="cb_gest_nomi_Zona4")
    btn7 = types.InlineKeyboardButton('Zona5',callback_data="cb_gest_nomi_Zona5")
    btn8 = types.InlineKeyboardButton('Zona6',callback_data="cb_gest_nomi_Zona6")
        
    markup_gest_nomi = types.InlineKeyboardMarkup(row_width=3)
    markup_gest_nomi.add(btn1,btn2)
    markup_gest_nomi.add(btn3,btn4,btn5,btn6,btn7,btn8)
    bot.send_message(message.chat.id, "Quale Nome vuoi cambiare ?", reply_markup=markup_gest_nomi)

def cattura_video(cam):
    print ('Sto registrando il video dalla webcam')
    #Capture video from webcam
    vid_capture = cv2.VideoCapture(int(cam))
    vid_cod = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    file_video="capture.mp4"
    output = cv2.VideoWriter(file_video, vid_cod, 20.0, (640,480))
    start_time = datetime.now()
    while(True):
        # Capture each frame of webcam video
        ret,frame = vid_capture.read()
        ##cv2.imshow("My cam video", frame)
        output.write(frame)
        # Close and break the loop after pressing "x" key
        time_delta = datetime.now() - start_time
        if time_delta.total_seconds() >= 5:
            break
    # close the already opened camera
    vid_capture.release()
    # close the already opened file
    output.release()
    # close the window and de-allocate any associated memory usage
    cv2.destroyAllWindows()
    
    return file_video

def cattura_stream(link):
    print ('Sto registrando il video dallo stream')
    file_video="capture.mp4"
    input = ffmpeg.input(str(link))
    #input = ffmpeg.input('rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4')
    #input = ffmpeg.input('rtsp://admin:Raffaele@192.168.1.101:554/Streaming/Channels/101/')
    video = input.trim(start=0, duration=10)
    video = ffmpeg.output(video, file_video)
    ffmpeg.run(video,overwrite_output=True,quiet=True) 
    
    return file_video

def video_verifica(zona):
    print ('Gestisco il video durante l\'allarme')
    cfgjsn=leggi_config()
    link_video=cfgjsn[str(zona)]
    print ('Link Video = '+link_video)
    
    if link_video=="":
        print('Nessun Video da gestire')
        return
    elif link_video.isnumeric()==True:
        print ('Gestico la webcam '+link_video)
        #cattura_video(link_video)
        file_video=cattura_video(link_video)
        invia_video(file_video)
    else:
        print ('Gestico lo stream '+link_video)
        
        file_video=cattura_stream(link_video)
        invia_video(file_video)
        
        
def invia_video(file_video):
    print ('Invio il video') 
    
    utenti=leggi_json()
    # ciclo di notifica agli utenti
    for utente in utenti:
        if utente['video_ver']=="True":
            bot.send_video(utente['id'],open(file_video, 'rb'),caption="Ecco il Video dell\'Allarme")     
        else:
            print ('Non invio il video')

def cambio_nome(message,nome):
    print ('cambio nome ...')
    chat_id = message.chat.id
    nome_new = message.text
    if isinstance(nome_new, str)==False:
        bot.send_message(chat_id,'Puoi inserire solo valori alfanumerici...',reply_markup=keyboard_admin())
        return
      
    try:
        
        print ('Hai modificato il nome di  ',nome ,' in ',nome_new)
        print ('scrivo sul file il nuovo nome...')
        
        in_file = open('config.json', 'r')
        data_file = in_file.read()
        data = json.loads(data_file)
        data[nome] = nome_new
        out_file = open('config.json','w')
        out_file.write(json.dumps(data,indent=4))
        out_file.close()
        global cfgjsn   
        cfgjsn=leggi_config()
        
        
        bot.send_message(chat_id,'Ho Modificato il nome di '+nome+' in '+nome_new,reply_markup=keyboard_admin())
    except Exception as e:
        print (e)
        bot.reply_to(message, "oooops c'è stato un errore nello scrivere il file di configurazione",reply_markup=keyboard_admin())
 
def scrivi_config(message,indice,valore):
    #print ('scrivi config ...')
    try:
        chat_id = message.chat.id
        in_file = open('config.json', 'r')
        data_file = in_file.read()
        data = json.loads(data_file)
        data[indice]=valore
        out_file = open('config.json','w')
        out_file.write(json.dumps(data,indent=4))
        out_file.close()
        global cfgjsn   
        cfgjsn=leggi_config()
        
        #print('Ho Modificato il nome valore di '+indice+' in '+valore )
        bot.send_message(chat_id,'Ho Modificato il nome valore di '+indice+' in '+valore )
    except Exception as e:
        print (e)
        bot.reply_to(message, "oooops c'è stato un errore nello scrivere il file di configurazione")
 
# Auto Inserimento---------------------------------------------------------------------------
# Variabile che contiene il timer
##t = None

# Routine che viene eseguita quando il timer scade
def FineTimer_ai() : 
    print("Timer Scaduto --->  ",time.asctime( time.localtime(time.time())))
    # ciclo di notifica agli utenti
    utenti=leggi_json()
    for utente in utenti:
        if utente['auto_ins']=="True":
            messaggio=  f"Ciao {utente['nome']}\n" \
                        f"Da diverso tempo nessun sensore segnala un movimento in casa e l'Allarme non è inserito.\n" \
                        f"<b>Vuoi Inserire l'allarme ora ?</b>"
            markup_ai = types.InlineKeyboardMarkup()
            btn_si = types.InlineKeyboardButton('SI',callback_data="cb_ai_SI")
            btn_no = types.InlineKeyboardButton('NO',callback_data="cb_ai_NO")
            btn_dopo = types.InlineKeyboardButton('Postponi...',callback_data="cb_ai_postponi")
            markup_ai.add(btn_si,btn_no,btn_dopo) 
            bot.send_message(utente['id'],messaggio,reply_markup=markup_ai,parse_mode='html')


cfgjsn=leggi_config()                   # leggo il file di configurazione
tempo_ai=int(cfgjsn['Timer_a_i'])*60    # imposto il tempo in minuti
timer=CountDown()
timer.start_timer(tempo_ai)
timer.stop_timer()

def Timer_ai():
    stati=json.loads(leggi_stati('stati'))  # leggo gli stati della centrale...
    cfgjsn=leggi_config()                   # leggo il file di configurazione
    tempo_ai=int(cfgjsn['Timer_a_i'])*60    # imposto il tempo in minuti
    now = datetime.now()
    ore=int(now.strftime("%H"))
    
    # Verifico :
    # - Che l'allarme non sia inserito
    # - Che la funzione sia abilitata 
    # - Che la fascia oraria sia quella corretta 
    # - Che tutte le zone siano a riposo...
    if (stati['area1']==False           and \
        stati['area2']==False           and \
        cfgjsn['Auto_Ins'] == "True"    and \
        ore >= int(cfgjsn['Start_a_i']) and \
        ore <  int(cfgjsn['Stop_a_i'] ) and \
        stati['z1']==False              and \
        stati['z2']==False              and \
        stati['z3']==False              and \
        stati['z4']==False              and \
        stati['z5']==False              and \
        stati['z6']==False              ):
            
            timer.start_timer(tempo_ai)
 
    else:
        print('NON attivo l\'auto inserimento in quanto qualche paramero non me lo consente !' )





# Fine Auto Inserimento----------------------------------------------------------------------




       
# Lista Utenti------------------------------------------------------------------------------------Lista Utenti 

# creo la collezione di callbackdata per la lista utenti da modificare
lista_utenti_factory = CallbackData('utente_id', prefix='utenti')

# Creo la funzione che crea i tasti da mostrare con la lista degli utenti 
def lista_utenti_keyboard():
        UTENTI=leggi_json()
        return types.InlineKeyboardMarkup(
            keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=utente['nome'],
                        callback_data=lista_utenti_factory.new(utente_id=utente['id'])
                    )
                ]
                for utente in UTENTI
                
            ]
            
        )
# Creo la funzione che crea il tasto indietro
def utenti_back_keyboard():
    return types.InlineKeyboardMarkup(
        keyboard=[
            [
                types.InlineKeyboardButton(
                    text='⬅',
                    callback_data='utenti_back'
                )
            ]
        ]
    )   
# Funzione chiamata dal menu
def lista_utenti(cb):
    bot.send_message(cb.message.chat.id, 'Lista Utenti:', reply_markup=lista_utenti_keyboard())
    
# Catturo le callback della lista utenti  
@bot.callback_query_handler(func=None, config=lista_utenti_factory.filter())
def utenti_callback(call: types.CallbackQuery):
    callback_data: dict = lista_utenti_factory.parse(callback_data=call.data)
    
    utente_id = int(callback_data['utente_id'])
    utente = leggi_utente(utente_id)
    simbolo_ins_area1=  '✅' if utente['ins_area1'] =='True'  else'🚫'
    simbolo_ins_area2=  '✅' if utente['ins_area2'] =='True'  else'🚫'
    simbolo_ins_totale= '✅' if utente['ins_totale']=='True'  else'🚫'
    simbolo_ins_smart=  '✅' if utente['ins_smart'] =='True'  else'🚫'
        
    simbolo_dis_area1=  '✅' if utente['dis_area1'] =='True'  else'🚫'
    simbolo_dis_area2=  '✅' if utente['dis_area2'] =='True'  else'🚫'
    simbolo_dis_totale= '✅' if utente['dis_totale']=='True'  else'🚫'
    simbolo_dis_smart=  '✅' if utente['dis_smart'] =='True'  else'🚫'
        
    simbolo_stato_area1=  '✅' if utente['stato_area1'] =='True'  else'🚫'
    simbolo_stato_area2=  '✅' if utente['stato_area2'] =='True'  else'🚫'
    simbolo_stato_smart= '✅' if utente['stato_smart']=='True'  else'🚫'
       
    simbolo_stato_allarme= '✅' if utente['stato_allarme']=='True'  else'🚫'
    simbolo_stato_guasti= '✅' if utente['stato_guasti']=='True'  else'🚫'
    
    simbolo_stato_z1= '✅' if utente['stato_z1']=='True'  else'🚫'
    simbolo_stato_z2= '✅' if utente['stato_z2']=='True'  else'🚫'
    simbolo_stato_z3= '✅' if utente['stato_z3']=='True'  else'🚫'
    simbolo_stato_z4= '✅' if utente['stato_z4']=='True'  else'🚫'
    simbolo_stato_z5= '✅' if utente['stato_z5']=='True'  else'🚫'
    simbolo_stato_z6= '✅' if utente['stato_z6']=='True'  else'🚫'
    
    simbolo_auto_ins=  '✅' if utente['auto_ins']=='True'  else'🚫'
    simbolo_video_ver= '✅' if utente['video_ver']=='True'  else'🚫'
    
    simbolo_admin= '✅' if utente['admin']=='True'  else'🚫'
    simbolo_owner= '✅' if utente['owner']=='True'  else'🚫'

    text =  f"<pre>\n" \
            f"ID        : {utente['id']}\n" \
            f"Nome      : {utente['nome']}\n" \
            f"Cognome   : {utente['cognome']}\n"\
            f"----------------------------------\n"\
            f"Inserisci Area 1 : {simbolo_ins_area1}       \n"\
            f"Dinserisci Area 1: {simbolo_dis_area1}       \n"\
            f"Stato Area 1     : {simbolo_stato_area1}     \n"\
            f"----------------------------------\n"\
            f"Inserisci Area 2 : {simbolo_ins_area2}       \n"\
            f"Dinserisci Area 2: {simbolo_dis_area2}       \n"\
            f"Stato Area 2     : {simbolo_stato_area2}     \n"\
            f"----------------------------------\n"\
            f"Inserisci  Totale: {simbolo_ins_totale}      \n"\
            f"Dinserisci Totale: {simbolo_dis_totale}      \n"\
            f"----------------------------------\n"\
            f"Inserisci Smart  : {simbolo_ins_smart}       \n"\
            f"Dinserisci Smart : {simbolo_dis_smart}       \n"\
            f"Stato Smart      : {simbolo_stato_smart}     \n"\
            f"----------------------------------\n"\
            f"Stato Zona 1     : {simbolo_stato_z1}        \n"\
            f"Stato Zona 2     : {simbolo_stato_z2}        \n"\
            f"Stato Zona 3     : {simbolo_stato_z3}        \n"\
            f"Stato Zona 4     : {simbolo_stato_z4}        \n"\
            f"Stato Zona 5     : {simbolo_stato_z5}        \n"\
            f"Stato Zona 6     : {simbolo_stato_z6}        \n"\
            f"----------------------------------\n"\
            f"Auto Insermento  : {simbolo_auto_ins}        \n"\
            f"Video Verifica   : {simbolo_video_ver}       \n"\
            f"----------------------------------\n"\
            f"Stato Allarme    : {simbolo_stato_allarme}   \n"\
            f"Stato Guasti     : {simbolo_stato_guasti}    \n"\
            f"----------------------------------\n"\
            f"Amministratore   : {simbolo_admin}   \n"\
            f"Proprietario     : {simbolo_owner}    \n"\
            f"</pre>\n" 
            
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=text, reply_markup=utenti_back_keyboard(),parse_mode='html')

# Catturo la callback del tasto Indietro   
@bot.callback_query_handler(func=lambda c: c.data == 'utenti_back')
def back_callback(call: types.CallbackQuery):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Lista Utenti:', reply_markup=lista_utenti_keyboard())

# Fine Lista Utenti------------------------------------------------------------------------------------Fine Lista Utenti
    
# Gestione Permessi--------------------------------------------------------------------------------------Gestione Permessi 

# creo la collezione di callbackdata per la lista utenti da modificare
gest_perm_utenti_factory = CallbackData('utente_id', prefix='gest_perm_utenti')
# Creo la funzione che crea i tasti da mostrare con la lista degli utenti da modificare
def gest_perm_utenti_keyboard():
        UTENTI=leggi_json()
        return types.InlineKeyboardMarkup(
            keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=utente['nome'],
                        callback_data=gest_perm_utenti_factory.new(utente_id=utente['id'])
                    )
                ]
                for utente in UTENTI
                
            ]
            
        )

# creo la collezione di callbackdata per la lista delle funzioni da modificare
gest_perm_funzioni_factory = CallbackData('funzione', prefix='gest_perm_funzioni',sep=':')
# Creo la funzione che crea i tasti da mostrare con la lista delle funzioni da modificare
def gest_perm_funzioni_keyboard(user_id):
    id=str(user_id)
    return types.InlineKeyboardMarkup(
            keyboard=[
                        [
                            types.InlineKeyboardButton(text='Inserisci Area 1',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,ins_area1,'+id)),
                            types.InlineKeyboardButton(text='Disinserisci Area 1',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,dis_area1,'+id)),
                        ],
                        [
                            types.InlineKeyboardButton(text='Stato Area 1',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_area1,'+id)),
                        ],
                        [
                            types.InlineKeyboardButton(text='-'*40,callback_data="----"),
                        ], 
                        [   
                            types.InlineKeyboardButton(text='Inserisci Area 2',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,ins_area2,'+id)),
                            types.InlineKeyboardButton(text='Disinserisci Area 2',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,dis_area2,'+id)),
                        ],
                        [
                            types.InlineKeyboardButton(text='Stato Area 2',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_area2,'+id)),
                        ],
                        [
                            types.InlineKeyboardButton(text='-'*40,callback_data="----"),
                        ],
                        [
                            types.InlineKeyboardButton(text='Inserisci Totale',     callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,ins_totale,'+id)),
                            types.InlineKeyboardButton(text='Disinserisci Totale',  callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,dis_totale,'+id)),
                        ],
                        [
                            types.InlineKeyboardButton(text='-'*40,callback_data="----"),
                        ],
                        [    
                            types.InlineKeyboardButton(text='Inserisci Smart',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,ins_smart,'+id)),
                            types.InlineKeyboardButton(text='Disinserisci Smart',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,dis_smart,'+id)),
                        ],
                        [
                            types.InlineKeyboardButton(text='Stato Smart',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_smart,'+id)),
                        ],
                        [
                            types.InlineKeyboardButton(text='-'*40,callback_data="----"),
                        ],
                        [
                            types.InlineKeyboardButton(text='Stato Zona 1',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_z1,'+id)),
                            types.InlineKeyboardButton(text='Stato Zona 2',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_z2,'+id))
                        ],
                        [
                            types.InlineKeyboardButton(text='Stato Zona 3',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_z3,'+id)),
                            types.InlineKeyboardButton(text='Stato Zona 4',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_z4,'+id))
                        ],
                        [
                            types.InlineKeyboardButton(text='Stato Zona 5',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_z5,'+id)),
                            types.InlineKeyboardButton(text='Stato Zona 6',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_z6,'+id))
                        ],
                        [
                            types.InlineKeyboardButton(text='-'*40,callback_data="----"),
                        ],
                        [
                            types.InlineKeyboardButton(text='Stato Allarme',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_allarme,'+id)),
                            types.InlineKeyboardButton(text='Stato Guasti',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,stato_guasti,'+id))
                        ],
                        [
                            types.InlineKeyboardButton(text='-'*40,callback_data="----"),
                        ],
                        [
                            types.InlineKeyboardButton(text='Auto Inserimento',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,auto_ins,'+id)),
                            types.InlineKeyboardButton(text='Video Verifica',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,video_ver,'+id))
                        ],
                        [
                            types.InlineKeyboardButton(text='-'*40,callback_data="----"),
                        ],
                        [
                            types.InlineKeyboardButton(text='Amministratore',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,admin,'+id))
                        ],
                        [
                            types.InlineKeyboardButton(text='Elimina Utente',callback_data=gest_perm_funzioni_factory.new(funzione='gest_perm,elimina,'+id))
                        ],
                        [
                            types.InlineKeyboardButton(text='⬅',callback_data='gest_perm_utenti_back')
                        ]
                    ]
        )

# creo la collezione di callbackdata per la lista delle funzioni da modificare
gest_perm_scelta_factory = CallbackData('scelta', prefix='gest_perm_scelta',sep=':')
# Creo la funzione che crea i tasti da mostrare con la scelta del valore da assegnare alle funzioni da modificare
def gest_perm_scelta_keyboard(funzione,user_id):
    id=str(user_id)
    return types.InlineKeyboardMarkup(
            keyboard=[
                        [
                            types.InlineKeyboardButton(text='SI',callback_data=gest_perm_scelta_factory.new(scelta='gest_perm,'+funzione+',SI,'+id)),
                            types.InlineKeyboardButton(text='NO',callback_data=gest_perm_scelta_factory.new(scelta='gest_perm,'+funzione+',NO,'+id)),
                        ],
                        [
                            types.InlineKeyboardButton(text='⬅',callback_data=gest_perm_scelta_factory.new(scelta='gest_perm,'+funzione+',BACK,'+id))
                        ]
                    ]
        )


def gest_permessi(cb):
    print ('Gestione Permessi ...') 
    bot.send_message(cb.message.chat.id, "Quale Utente vuoi gestire ?", reply_markup=gest_perm_utenti_keyboard())

# Catturo le callback della lista utenti che voglio modificare
@bot.callback_query_handler(func=None, config=gest_perm_utenti_factory.filter())
def gest_perm_utenti_callback(call: types.CallbackQuery):
    callback_data: dict = gest_perm_utenti_factory.parse(callback_data=call.data)
    
    utente_id = int(callback_data['utente_id'])
    utente = leggi_utente(utente_id)
              
    bot.send_message(call.message.chat.id, 'Quale permesso di <b>'+str(utente['nome'])+'</b> vuoi modificare ?', reply_markup=gest_perm_funzioni_keyboard(utente_id),parse_mode='html')
  
# Catturo le callback dei tipi di funzioni  
@bot.callback_query_handler(func=None, config=gest_perm_funzioni_factory.filter())
def gest_perm_funz_callback(call: types.CallbackQuery):
    callback_data: dict = gest_perm_funzioni_factory.parse(callback_data=call.data)
    dato = str(callback_data['funzione'])
    funzione=dato.split(',')[1]
    id_utente=int(dato.split(',')[2])
    utente = leggi_utente(id_utente)
    if funzione=='elimina':
        bot.send_message(call.message.chat.id,"Vuoi <b>ELIMIARE</b> l'utente <b> "+utente['nome']+"</b> ?",reply_markup=gest_perm_scelta_keyboard(funzione,id_utente),parse_mode='html')
    else:
        bot.send_message(call.message.chat.id,"Vuoi che <b>"+utente['nome']+"</b> sia abilitato alla funzione <b>\""+funzione+"\"</b> ?",reply_markup=gest_perm_scelta_keyboard(funzione,id_utente),parse_mode='html')
    
# Catturo le callback delle scelte delle funzioni  
@bot.callback_query_handler(func=None, config=gest_perm_scelta_factory.filter())
def gest_perm_scelta_callback(call: types.CallbackQuery):
    callback_data: dict = gest_perm_scelta_factory.parse(callback_data=call.data)
    dato = str(callback_data['scelta'])
    funzione=dato.split(',')[1]
    scelta=str(dato.split(',')[2])
    id_utente=int(dato.split(',')[3])
    utente = leggi_utente(id_utente)    
    
    if scelta=='BACK':
        print ('torno al menu dell\'utente')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Quale permesso di <b>'+str(utente['nome'])+'</b> vuoi modificare ?', reply_markup=gest_perm_funzioni_keyboard(id_utente),parse_mode='html')
    elif scelta=='SI':
        if funzione=='elimina':
            if elimina_utente(id_utente)==True:
                bot.send_message(call.message.chat.id,'Utente Eliminato Correttamente')
                log(call.from_user.first_name +' ha Eliminato l\' utente '+ str(utente['nome']))
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                            text='Quale permesso di <b>'+str(utente['nome'])+'</b> vuoi modificare ?', reply_markup=gest_perm_funzioni_keyboard(id_utente),parse_mode='html')
    
        else:
            if scrivi_json(id_utente,funzione,'True')==True:
                bot.send_message(call.message.chat.id,'Funzione Modificata Correttamente')
                log(call.from_user.first_name +' ha Abilitato la funzione \"'+ str(funzione) + '\" all\'utente '+str(utente['nome']))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                            text='Quale permesso di <b>'+str(utente['nome'])+'</b> vuoi modificare ?', reply_markup=gest_perm_funzioni_keyboard(id_utente),parse_mode='html')
    elif scelta=='NO':
        if funzione=='elimina':
            print ('NON elimino l\'utente -> ',id_utente )
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                            text='Quale permesso di <b>'+str(utente['nome'])+'</b> vuoi modificare ?', reply_markup=gest_perm_funzioni_keyboard(id_utente),parse_mode='html')
    
        else:
            if scrivi_json(id_utente,funzione,'False')==True:
                bot.send_message(call.message.chat.id,'Funzione Modificata Correttamente')
                log(call.from_user.first_name +' ha Disabilitato la funzione \"'+ str(funzione) + '\" all\'utente '+str(utente['nome']))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Quale permesso di <b>'+str(utente['nome'])+'</b> vuoi modificare ?', reply_markup=gest_perm_funzioni_keyboard(id_utente),parse_mode='html')

# Catturo la callback del tasto Indietro
@bot.callback_query_handler(func=lambda c: c.data == 'gest_perm_utenti_back')
def gest_perm_back_callback(call: types.CallbackQuery):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Quale Utente vuoi gestire ?', reply_markup=gest_perm_utenti_keyboard())

# FINE Gestione Permessi -------------------------------------------------------------------------FINE Gestione Permessi 


# Gestione Servizi--------------------------------------------------------------------------------Gestione Servizi

# creo la collezione di callbackdata per la lista utenti da modificare
gest_servizi_factory = CallbackData('servizio', prefix='gest_servizi')
# Creo la funzione che crea i tasti da mostrare con la lista degli utenti da modificare
def gest_servizi_keyboard():
    return types.InlineKeyboardMarkup(
            keyboard=[
                        [
                            types.InlineKeyboardButton(text='VPN',callback_data=gest_servizi_factory.new(servizio='vpn')),
                            types.InlineKeyboardButton(text='SSH',callback_data=gest_servizi_factory.new(servizio='ssh')),
                        ],
                        [
                            types.InlineKeyboardButton(text='KyoBot',callback_data=gest_servizi_factory.new(servizio='kyobot')),
                        ]
                    ]
        )

# creo la collezione di callbackdata per la scelta dei servizi da modificare
gest_servizi_scelta_factory = CallbackData('scelta', prefix='gest_servizi_scelta',sep=':')
# Creo la funzione che crea i tasti da mostrare con la scelta del valore da assegnare ai servizi da modificare
def gest_servizio_scelta_keyboard(servizio):
    return types.InlineKeyboardMarkup(
            keyboard=[
                        [
                            types.InlineKeyboardButton(text='Avvia',callback_data=gest_servizi_scelta_factory.new(scelta=servizio+',start')),
                            types.InlineKeyboardButton(text='Stoppa',callback_data=gest_servizi_scelta_factory.new(scelta=servizio+',stop')),
                        ],
                        [
                            types.InlineKeyboardButton(text='⬅',callback_data='Servizi_Back')
                        ]
                    ]
        )

def gest_servizi(cb):
    print ('Gestione Servizi ...') 
    bot.send_message(cb.message.chat.id, "Quale Servizio vuoi gestire ?", reply_markup=gest_servizi_keyboard())

# Catturo le callback dei servizi che voglio modificare
@bot.callback_query_handler(func=None, config=gest_servizi_factory.filter())
def gest_servizi_callback(call: types.CallbackQuery):
    callback_data: dict = gest_servizi_factory.parse(callback_data=call.data)
    servizio = str(callback_data['servizio'])
    stato_servizio=stato_servizi(servizio)
    print ('Servizio = ',servizio , ' --> ', stato_servizio)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Lo stato del Servizio '+servizio +' è : \n <b>'+stato_servizio+'</b>.\n Cosa vuoi Fare ?', reply_markup=gest_servizio_scelta_keyboard(servizio),parse_mode='html')

# Catturo le callback della scelta dei servizi che voglio modificare
@bot.callback_query_handler(func=None, config=gest_servizi_scelta_factory.filter())
def gest_servizi_scelta_callback(call: types.CallbackQuery):
    callback_data: dict = gest_servizi_scelta_factory.parse(callback_data=call.data)
    dato = str(callback_data['scelta'])
    servizio=dato.split(',')[0]
    scelta=str(dato.split(',')[1])
    esito = gest_servizio(servizio,scelta)
    stato_servizio=stato_servizi(servizio)
    if (esito=='avviato'or esito=='stoppato'):
        log(call.from_user.first_name +' ha '+esito+' il servizio '+servizio)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Il servizio '+servizio +' è stato  <b>'+esito+'</b>.\n Lo stato del Servizio '+servizio +' è : \n <b>'+stato_servizio+'</b>.\n Cosa vuoi Fare ?', reply_markup=gest_servizio_scelta_keyboard(servizio),parse_mode='html')
    else:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Il servizio '+servizio +' è   <b>'+esito+'</b>.\n Lo stato del Servizio '+servizio +' è : \n <b>'+stato_servizio+'</b>.\n Cosa vuoi Fare ?', reply_markup=gest_servizio_scelta_keyboard(servizio),parse_mode='html')

# Catturo la callback del tasto Indietro
@bot.callback_query_handler(func=lambda c: c.data == 'Servizi_Back')
def gest_servizi_back_callback(call: types.CallbackQuery):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text='Quale Servizio vuoi gestire ?', reply_markup=gest_servizi_keyboard())

# FINE Gestione Servizi---------------------------------------------------------------------------FINE Gestione Servizi

def NotificaAllarme(tipo,stato,zona):
    utenti=leggi_json()
    zone=json.loads(leggi_stati('stati'))
    # preparo i messaggi da scrivere sul log e sugli avvisi
    msg_allarme=''
    msg_allarme_log=''
    if zone['z1']==True:
        msg_allarme=msg_allarme+cfgjsn['Zona1']+'\n'
        msg_allarme_log=msg_allarme_log+cfgjsn['Zona1']+', '
    if zone['z2']==True:
        msg_allarme=msg_allarme+cfgjsn['Zona2']+'\n'
        msg_allarme_log=msg_allarme_log+cfgjsn['Zona2']+', '
    if zone['z3']==True:
        msg_allarme=msg_allarme+cfgjsn['Zona3']+'\n'
        msg_allarme_log=msg_allarme_log+cfgjsn['Zona3']+', '
    if zone['z4']==True:
        msg_allarme=msg_allarme+cfgjsn['Zona4']+'\n'
        msg_allarme_log=msg_allarme_log+cfgjsn['Zona4']+', '
    if zone['z5']==True:
        msg_allarme=msg_allarme+cfgjsn['Zona5']+'\n'
        msg_allarme_log=msg_allarme_log+cfgjsn['Zona5']+', '
    if zone['z6']==True:
        msg_allarme=msg_allarme+cfgjsn['Zona6']+'\n'
        msg_allarme_log=msg_allarme_log+cfgjsn['Zona6']+'.'

    # azioni da fare quando l'allarme suona o smette di suonare
    if stato=='attivo':
            print ("Attenzione Allarme in Corso nelle seguenti zone :\n"+msg_allarme)
            log('Allarme in Corso nelle seuenti zone ...  '+msg_allarme_log)
            global stato_allarme
            stato_allarme=True
    else:
            stato_allarme=False
            print ("Allarme Cessato" )
            log('Allarme Cessato')
            
    # ciclo di notifica agli utenti
    for utente in utenti:
        if tipo=='centrale':
            if utente['stato_allarme']=="True":
                if stato=='attivo':
                    bot.send_message(utente['id'],"Allarme in Corso nelle seguenti zone :\n"+msg_allarme)
                    bot.send_video(utente['id'],open('ring-bell.mp4', 'rb'))
                else:
                    bot.send_message(utente['id'],'Allarme Cessato')#bot.send_video(utente['id'],open(file_video, 'rb'),caption="Ecco il Video del Cessato Allarme")
        if tipo=='smart':
            if utente['stato_smart']=="True":
                if stato=='attivo':
                    bot.send_message(utente['id'],"<b>ALLARME SMART in Corso</b> nelle seguenti zone :\n"+msg_allarme,parse_mode='html')
                    bot.send_video(utente['id'],open('ring-bell.mp4', 'rb'))#bot.send_video(utente['id'],open(file_video, 'rb'),caption="Ecco il Video dell'Allarme in Corso")
                else:
                    bot.send_message(utente['id'],'<b>ALLARME SMART Cessato</b> nella zona : '+cfgjsn[zona],parse_mode='html')
                         

# callBack dei cambi stato dei pin della centrale
def cb_oc1(gpio):
    utenti=leggi_json()
    for utente in utenti:
        if utente['stato_area1']=="True":
            if GPIO.input(pin_oc1)==1:
                global stato_area1
                stato_area1=False
                bot.send_message(utente['id'],cfgjsn['Area1']+' Disinserito...')
                log(cfgjsn['Area1']+' Disinserito...')
            else:
                stato_area1=True
                bot.send_message(utente['id'],cfgjsn['Area1']+' Inserito...')
                log(cfgjsn['Area1']+' Inserito...')
    
def cb_oc2(gpio):
    utenti=leggi_json()
    for utente in utenti:
        if utente['stato_area2']=="True":
            if GPIO.input(pin_oc2)==1:
                global stato_area2
                stato_area2=False
                bot.send_message(utente['id'],cfgjsn['Area2']+' Disinserito...')
                log(cfgjsn['Area2']+' Disinserito...')
            else:
                stato_area2=True
                bot.send_message(utente['id'],cfgjsn['Area2']+' Inserito...')
                log(cfgjsn['Area2']+' Inserito...')

def cb_oc3(gpio):
    utenti=leggi_json()
    for utente in utenti:
        if utente['stato_guasti']=="True":
            if GPIO.input(pin_oc3)==1:
                bot.send_message(utente['id'],' Nessun Guasto Attivo Sulla Centrale Kyo')
                log('Nessun Guasto Attivo Sulla Centrale')
            else:
                bot.send_message(utente['id'],'⚠️ Attenzione c\'è un Guasto sulla Centrale Kyo ⚠️')
                log('Attenzione c\'è un Guasto sulla Centrale')
 

def cb_no(gpio):
    if GPIO.input(pin_no)==0:
        NotificaAllarme('centrale','attivo','sirena')
    else:
        NotificaAllarme('centrale','cessato','sirena')

def cb_z1(gpio):
    #print ('lo stato di z1 ( ',cfgjsn['Zona1'],' ) è cambiato e ora vale ',GPIO.input(pin_z1))
    cfgjsn=leggi_config()
    if GPIO.input(pin_z1)==0:#Rilevato movimento
        print(cfgjsn["Zona1"],' --> ON' )        
        if cfgjsn['Smart']=='True':
            print ('Allarme Smart Attivo')
            NotificaAllarme('smart','attivo','Zona1')
            if cfgjsn['Video']=='True':
                video_verifica('Video1')
        else:
            timer.stop_timer()
            
    else:#Nessun movimento rilevato
        print(cfgjsn["Zona1"],' --> OFF' )
        if cfgjsn['Smart']=='True': 
            print ('Allarme Smart Cessato')
            NotificaAllarme('smart','cessato','Zona1')
        else:   
            Timer_ai()

def cb_z2(gpio):
    #print ('lo stato di z2 ( ',cfgjsn['Zona2'],' ) è cambiato e ora vale ',GPIO.input(pin_z2))
    if GPIO.input(pin_z2)==0:#Rilevato movimento 
        print(cfgjsn["Zona2"],' --> ON' )       
        if cfgjsn['Smart']=='True':
            print ('Allarme Smart Attivo')
            NotificaAllarme('smart','attivo','Zona2')
            if cfgjsn['Video']=='True':
                video_verifica('Video2')
        else:
            timer.stop_timer()
            
    else:#Nessun movimento rilevato
        print(cfgjsn["Zona2"],' --> OFF' ) 
        if cfgjsn['Smart']=='True': 
            print ('Allarme Smart Cessato')
            NotificaAllarme('smart','cessato','Zona2')
        else:
            Timer_ai()

def cb_z3(gpio):
    #print ('lo stato di z3 ( ',cfgjsn['Zona3'],' ) è cambiato e ora vale ',GPIO.input(pin_z3))
    if GPIO.input(pin_z3)==0:#Rilevato movimento
        print(cfgjsn["Zona3"],' --> ON' )         
        if cfgjsn['Smart']=='True':
            print ('Allarme Smart Attivo')
            NotificaAllarme('smart','attivo','Zona3')
            if cfgjsn['Video']=='True':
                video_verifica('Video3')
        else:
            timer.stop_timer()
            
    else:#Nessun movimento rilevato
        print(cfgjsn["Zona3"],' --> OFF' )
        if cfgjsn['Smart']=='True': 
            print ('Allarme Smart Cessato')
            NotificaAllarme('smart','cessato','Zona3')
        else: 
            Timer_ai()

def cb_z4(gpio):
    #print ('lo stato di z4 ( ',cfgjsn['Zona4'],' ) è cambiato e ora vale ',GPIO.input(pin_z4))
    if GPIO.input(pin_z4)==0:#Rilevato movimento 
        print(cfgjsn["Zona4"],' --> OFF' )       
        if cfgjsn['Smart']=='True':
            print ('Allarme Smart Attivo')
            NotificaAllarme('smart','attivo','Zona4')
            if cfgjsn['Video']=='True':
                video_verifica('Video4')
        else:
            timer.stop_timer()
            
    else:#Nessun movimento rilevato
        print(cfgjsn["Zona4"],' --> OFF' )
        if cfgjsn['Smart']=='True': 
            print ('Allarme Smart Cessato')
            NotificaAllarme('smart','cessato','Zona4')
        else: 
            Timer_ai()
   
def cb_z5(gpio):
    #print ('lo stato di z5 ( ',cfgjsn['Zona5'],' ) è cambiato e ora vale ',GPIO.input(pin_z5))
    if GPIO.input(pin_z5)==0:#Rilevato movimento  
        print(cfgjsn["Zona5"],' --> ON' )      
        if cfgjsn['Smart']=='True':
            print ('Allarme Smart Attivo')
            NotificaAllarme('smart','attivo','Zona5')
            if cfgjsn['Video']=='True':
                video_verifica('Video5')
        else:
            timer.stop_timer()
            
    else:#Nessun movimento rilevato
        print(cfgjsn["Zona5"],' --> OFF' )
        if cfgjsn['Smart']=='True': 
            print ('Allarme Smart Cessato')
            NotificaAllarme('smart','cessato','Zona5')
        else:
            Timer_ai() 
            
  
def cb_z6(gpio):
    #print ('lo stato di z6 ( ',cfgjsn['Zona6'],' ) è cambiato e ora vale ',GPIO.input(pin_z6))
    if GPIO.input(pin_z6)==0:#Rilevato movimento
        print(cfgjsn["Zona6"],' --> ON' )        
        if cfgjsn['Smart']=='True':
            print ('Allarme Smart Attivo')
            NotificaAllarme('smart','attivo','Zona6')
            if cfgjsn['Video']=='True':
                video_verifica('Video6')
        else:
            timer.stop_timer()
            print('Timer stoppato da  z6 ( ',cfgjsn['Zona6'],' )')
    else:#Nessun movimento rilevato
        print(cfgjsn["Zona6"],' --> OFF' ) 
        if cfgjsn['Smart']=='True': 
            print ('Allarme Smart Cessato')
            NotificaAllarme('smart','cessato','Zona6')
        else:
            Timer_ai()
            

                
#-------------------------------------------------------------  
 
# Quando un pin cambia stato...
cb1=GPIO.add_event_detect(pin_oc1, GPIO.BOTH, callback=cb_oc1, bouncetime=800)
cb2=GPIO.add_event_detect(pin_oc2, GPIO.BOTH, callback=cb_oc2, bouncetime=800)
cb3=GPIO.add_event_detect(pin_oc3, GPIO.BOTH, callback=cb_oc3, bouncetime=800)

no=GPIO.add_event_detect(pin_no, GPIO.BOTH, callback=cb_no, bouncetime=400) 
z1=GPIO.add_event_detect(pin_z1, GPIO.BOTH, callback=cb_z1, bouncetime=400)
z2=GPIO.add_event_detect(pin_z2, GPIO.BOTH, callback=cb_z2, bouncetime=400)
z3=GPIO.add_event_detect(pin_z3, GPIO.BOTH, callback=cb_z3, bouncetime=400)
z4=GPIO.add_event_detect(pin_z4, GPIO.BOTH, callback=cb_z4, bouncetime=400)
z5=GPIO.add_event_detect(pin_z5, GPIO.BOTH, callback=cb_z5, bouncetime=400)
z6=GPIO.add_event_detect(pin_z6, GPIO.BOTH, callback=cb_z6, bouncetime=400)
#z1=GPIO.add_event_detect(pin_z1, GPIO.RISING, callback=cb_z1_rising, bouncetime=800)
#z1=GPIO.add_event_detect(pin_z1, GPIO.FALLING, callback=cb_z1_falling, bouncetime=800)# 


    
# catturo i comandi /start e /help
@bot.message_handler(commands=['start', 'help' , 'aiuto','menu','Menu','menù','Menù'])
def send_welcome(message):
    
    if is_member(message.chat.id)==True:    # Se l'utente è presente nella lista Dagli il menu
        
        if message.chat.type=='private':        # Se il messaggio arriva da una chat privata...
            bot.send_message(message.chat.id, "Benvenuto "+ message.from_user.first_name+', usa il menu qui sotto per gestire la tua centrale.\nSe non lo hai già fatto, ti consiglio di leggere le istruzioni usando l\'apposito tasto.', reply_markup=keyboard_admin())
        elif message.chat.type=='group':        # Se il messaggio arriva da una chat di gruppo...
            bot.send_message(message.chat.id,  message.from_user.first_name+' NON puoi gestire l\'allarme da questo gruppo')
    else:                                   # Se l'utente non è presente nella lista 
        menu_not_member(message)

# catturo il comando /upgrade
@bot.message_handler(commands=['upgrade'])
def upgrade(message):
    nome=message.from_user.first_name
    testoV11 =  f"Ciao {nome}!\n" \
                f"Il team di Sviluppo è lieto di annunciarti che le modifiche da te richieste sono state eseguite...\n\n" \
                f"In questa versione (V1.1,13112022) sono state apportate le seguenti modifiche:\n\n" \
                f"- Aggiunto il tasto <b>\"Totale\"</b> nel menù Inserisci e Disinserisci\n\n"\
                f"- Migliorata la gestione dei Thread nella routine di Auto Inserimento" 
    utenti=leggi_json()
    # ciclo di notifica agli utenti
    for utente in utenti:
        bot.send_message(utente['id'], testoV11,parse_mode='html')
    
  
       
# Catturo i messaggi di saluto
@bot.message_handler(text=['ciao','Ciao','cia','Cia'])
def text_filter(message):
    bot.send_message(message.chat.id, "Ciao, {name}!".format(name=message.from_user.first_name))
    
# Catturo i messaggi di easter eggs
@bot.message_handler(text=['Cavallo','cavallo'])
def easter_egg(message):
    markup_cav = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('SI',callback_data="cb_ee_cav_si")
    btn2 = types.InlineKeyboardButton('NO',callback_data="cb_ee_cav_NO")
    markup_cav.add(btn1,btn2)
    bot.send_message(message.chat.id, "{name}, Hai detto Cavallo ?".format(name=message.from_user.first_name),reply_markup=markup_cav)
@bot.message_handler(text=['Drogau','drogau'])
def easter_egg_2(message):
    bot.send_video(message.chat.id,open('ee2.mp4', 'rb'),caption="Tui sesi Drogau...",)     
   
          
# catturo tutti i messaggi
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    if(message.text=='Istruzioni'):
        istruzioni(message) 
    elif(message.text=='⚙️ Admin ⚙️'):
        menu_admin(message)
    elif(message.text=='Info'):
        info(message)
    elif(message.text=='Inserisci'):
        menu_inserisci(message)
    elif(message.text=='Disinserisci'):
        menu_disinserisci(message)
    elif(message.text=='Stato'):
        menu_stato(message.chat.id)
    elif(message.text=='menu'):
        if is_member(message.chat.id)==True:    # Se l'utente è presente nella lista Dagli il menu
        
            if message.chat.type=='private':        # Se il messaggio arriva da una chat privata...
                bot.send_message(message.chat.id, "Benvenuto "+ message.from_user.first_name+', usa il menu qui sotto per gestire la tua centrale.\nSe non lo hai già fatto, ti consiglio di leggere le istruzioni usando l\'apposito tasto.', reply_markup=keyboard_admin())
            elif message.chat.type=='group':        # Se il messaggio arriva da una chat di gruppo...
                bot.send_message(message.chat.id,  message.from_user.first_name+' NON puoi gestire l\'allarme da questo gruppo')
        else:                                   # Se l'utente non è presente nella lista 
            menu_not_member(message)
    
    else:
        print ('Hanno scritto ... ',message.reply_to_message)

@bot.message_handler(func=lambda query:True)      
def query_all(message):
    print ('Query...')
   
# catturo il testo della callback dell'easter egg
@bot.callback_query_handler(func=lambda c: c.data == 'cb_ee_cav_si')
def cb_ee_cav_si(call: types.CallbackQuery):
    bot.answer_callback_query(callback_query_id=call.id, text='       TI CODDIDI !!! 🙈🙈🙈', show_alert=True)

     
# catturo le callback di Telegram
@bot.callback_query_handler(func=lambda call: True)
def callback(cb): # <- passes a CallbackQuery type object to your function
    #print('CallBack ---> ',cb.from_user.id)
    nome=cb.from_user.first_name
    

   # callBack di Inserimento
    if(cb.data=='cb_ins_area1'):
        inserisci('Area1',cb.message)
    elif(cb.data=='cb_ins_area2'):
        inserisci('Area2',cb.message)
    elif(cb.data=='cb_ins_totale'):
        inserisci('Totale',cb.message)
    elif(cb.data=='cb_ins_smart'):
        inserisci('Smart',cb.message)

    # CallBack di conferma Inserimento
    elif(cb.data=='cb_ins_A1_SI'):
        bot.send_message(cb.message.chat.id, "OK "+nome+" Inserisco "+cfgjsn['Area1']+" ...")
        print (nome," Ha inserito ",cfgjsn['Area1'])
        GPIO.output(pin_area1, True)
        time.sleep(1)
        GPIO.output(pin_area1, False)
        log(nome+" Ha Inserito "+cfgjsn['Area1'])
    elif(cb.data=='cb_ins_A2_SI'):
        bot.send_message(cb.message.chat.id, "OK "+nome+" Inserisco "+cfgjsn['Area2']+" ...")
        print (nome," Ha inserito "+cfgjsn['Area2'])
        GPIO.output(pin_area2, True)
        time.sleep(1)
        GPIO.output(pin_area2, False)
        log(nome+" Ha Inserito "+cfgjsn['Area2'])
    elif(cb.data=='cb_ins_Tot_SI'):
        bot.send_message(cb.message.chat.id, "OK "+nome+" Inserisco il Totale ...")
        # leggi lo stato della centrale
        stati=json.loads(leggi_stati('stati'))
        if stati['area2']==False:
            print (nome," Ha inserito "+cfgjsn['Area2'])
            GPIO.output(pin_area2, True)
            time.sleep(1)
            GPIO.output(pin_area2, False)
            log(nome+" Ha Inserito "+cfgjsn['Area2'])
        if stati['area1']==False:
            print (nome," Ha inserito "+cfgjsn['Area1'])
            GPIO.output(pin_area1, True)
            time.sleep(1)
            GPIO.output(pin_area1, False)
            log(nome+" Ha Inserito "+cfgjsn['Area1'])
    elif(cb.data=='cb_ins_S_SI'):
        scrivi_config(cb.message,'Smart','True')
        bot.send_message(cb.message.chat.id, "OK "+nome+" Inserisco l\'<b>Allarme Smart</b>",parse_mode='html')
        print (nome+" Raffaele Ha inserito l'Allarme Smart")
        log(nome+" Ha Inserito l'Allarme Smart")
    
    # CallBack di annullamento    
    elif(cb.data=='cb_ins_NO'):
        bot.send_message(cb.message.chat.id, "OK NON faccio nulla")   
        
    # callBack di Disinserimento
    elif(cb.data=='cb_dis_area1'):
        disinserisci('Area1',cb.message)
    elif(cb.data=='cb_dis_area2'):
        disinserisci('Area2',cb.message)
    elif(cb.data=='cb_dis_totale'):
        disinserisci('Totale',cb.message)
    elif(cb.data=='cb_dis_smart'):
        disinserisci('Smart',cb.message)

    # CallBack di conferma Disinserimento
    elif(cb.data=='cb_dis_A1_SI'):
        bot.send_message(cb.message.chat.id, "OK "+nome+" Disinserisco "+cfgjsn['Area1']+" ...")
        print (nome," Ha Disinserito "+cfgjsn['Area1'])
        GPIO.output(pin_area1, True)
        time.sleep(1)
        GPIO.output(pin_area1, False)
        log(nome+" Ha Disinserito "+cfgjsn['Area1'])
    elif(cb.data=='cb_dis_A2_SI'):
        bot.send_message(cb.message.chat.id, "OK "+nome+" Disinserisco "+cfgjsn['Area2']+" ...")
        print (nome," Ha Disinserito "+cfgjsn['Area2'])
        GPIO.output(pin_area2, True)
        time.sleep(1)
        GPIO.output(pin_area2, False)
        log(nome+" Ha Disinserito "+cfgjsn['Area2'])
    elif(cb.data=='cb_dis_Tot_SI'):
        bot.send_message(cb.message.chat.id, "OK "+nome+" Disinserisco il Totale ...")
        # leggi lo stato della centrale
        stati=json.loads(leggi_stati('stati'))
        if stati['area2']==True:
            print (nome," Ha disinserito "+cfgjsn['Area2'])
            GPIO.output(pin_area2, True)
            time.sleep(1)
            GPIO.output(pin_area2, False)
            log(nome+" Ha Disinserito "+cfgjsn['Area2'])
        if stati['area1']==True:
            print (nome," Ha disinserito "+cfgjsn['Area1'])
            GPIO.output(pin_area1, True)
            time.sleep(1)
            GPIO.output(pin_area1, False)
            log(nome+" Ha Disnserito "+cfgjsn['Area1'])
    elif(cb.data=='cb_dis_S_SI'):
        scrivi_config(cb.message,'Smart','False')
        bot.send_message(cb.message.chat.id, "OK "+nome+" Disinserisco l\'<b>Allarme Smart</b>",parse_mode='html')
        print (nome+ " Ha Disinserito l'Allarme Smart")
        log(nome+" Ha Disinserito l'Allarme Smart")

    # CallBack di annullamento    
    elif(cb.data=='cb_dis_NO'):
        bot.send_message(cb.message.chat.id, "OK NON faccio nulla") 
        
    # CallBack Stato
    elif(cb.data=='cb_stato'):
        bot.send_message(cb.message.chat.id, nome+ " da questo menu puoi solo visualizzare lo stato dell'impianto.\n Se vuoi Inserire o Disinserire l\'impianto usa il menu qui sotto...")     
        
    # CallBack Not_Member
    elif(cb.data=='not_member_SI'):
        not_member(cb)
        global membro_new
        membro_new=cb
        bot.send_message(cb.message.chat.id, "Ho inviato la richiesta all\'amministratore...\nAttendi la risposta") 
     
    elif(cb.data=='not_member_NO'):
        bot.send_message(cb.message.chat.id, "Va bene "+nome+" è stato un piacere conoscerti.") 
     
    # CallBack ADD Not_Member
    elif(cb.data=='add_not_member_SI'):
        bot.send_message(cb.message.chat.id, "Ok  aggiorno il file di configurazione...")
        print ('Aggiorno il file json...')
        if add_user(membro_new)==True:
            bot.send_message(cb.message.chat.id, "Ho aggiunto "+membro_new.from_user.first_name+".\nVai sul menu Admin e gestisci i permessi !!!")
            print ('utente aggiunto correttamente')
            log(nome+" Ha aggiunto "+membro_new.from_user.first_name+ " alla lista degli utenti abilitati")
            bot.send_message(membro_new.from_user.id, membro_new.from_user.first_name+" sei stato autorizzato all\'utilizzo dell\'allarme.\nUsa il menu qui sotto per gestire la tua centrale.\nSe non lo hai già fatto, ti consiglio di leggere le istruzioni usando l\'apposito tasto.", reply_markup=keyboard_admin())
            
        else:
            bot.send_message(cb.message.chat.id, "Errore nell\'aggiungere "+membro_new.from_user.first_name+" al file di configurazione 😱😱😱")
            print ('Errore nell\' aggiunta utente')
            log("C\'è stato un errore nell\'aggiunta dell\'utente "+membro_new.from_user.first_name)
            bot.send_message(membro_new.from_user.id, "Errore nell\'aggiungere "+membro_new.from_user.first_name+" al file di configurazione 😱😱😱")
           
            
    elif(cb.data=='add_not_member_NO'):
        bot.send_message(cb.message.chat.id, "Ok  lo mando a cagare subito. 🤣🤣🤣") 
        log(nome +" ha rifiutato di aggiungere "+ membro_new.from_user.first_name + " alla lista degli utenti abilitati")
           
    # CallBack di funzione vietata   
    elif(cb.data=='cb_funz_vietata'):
        bot.send_message(cb.message.chat.id, "🚫 NON sei abilitato ad usare questa funzione !!!")
   
     # CallBack di lettura log   
    elif(cb.data=='cb_leggi_log'):
        logs=leggi_log(30)
        bot.send_message(cb.message.chat.id, logs,parse_mode='html')
        
    # CallBack Lista Utenti   
    elif(cb.data=='cb_lista_utenti'):
        lista_utenti(cb)
        
    # CallBack di gestione permessi   
    elif(cb.data=='cb_gest_permessi'):
        gest_permessi(cb)
        
    # CallBack di gestione servizi   
    elif(cb.data=='cb_gest_servizi'):
        gest_servizi(cb)
    
    # CallBack di stato hardware   
    elif(cb.data=='cb_stato_hw'):
        stato_hw(cb) 
    # CallBack di stato Rete   
    elif(cb.data=='cb_stato_net'):
        stato_net(cb)
    
    # CallBack di gestione nomi  
    elif(cb.data=='cb_gest_nomi'):
        gest_nomi(cb.message)
    elif(cb.data=='cb_gest_nomi_Area1'):
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il NUOVO nome')
        msg=bot.send_message(cb.message.chat.id,'il nome attuale è ... '+cfgjsn['Area1']+'. Inserisci il nuovo nome...' ,parse_mode='html',reply_markup=markup_force_reply,)
        bot.register_next_step_handler(msg, cambio_nome,'Area1')
    elif(cb.data=='cb_gest_nomi_Area2'):
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il NUOVO nome')
        msg=bot.send_message(cb.message.chat.id,'il nome attuale è ... '+cfgjsn['Area2']+'. Inserisci il nuovo nome...' ,parse_mode='html',reply_markup=markup_force_reply,)
        bot.register_next_step_handler(msg, cambio_nome,'Area2')
    elif(cb.data=='cb_gest_nomi_Zona1'):
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il NUOVO nome')
        msg=bot.send_message(cb.message.chat.id,'il nome attuale è ... '+cfgjsn['Zona1']+'. Inserisci il nuovo nome...' ,parse_mode='html',reply_markup=markup_force_reply,)
        bot.register_next_step_handler(msg, cambio_nome,'Zona1')
    elif(cb.data=='cb_gest_nomi_Zona2'):
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il NUOVO nome')
        msg=bot.send_message(cb.message.chat.id,'il nome attuale è ... '+cfgjsn['Zona2']+'. Inserisci il nuovo nome...' ,parse_mode='html',reply_markup=markup_force_reply,)
        bot.register_next_step_handler(msg, cambio_nome,'Zona2')
    elif(cb.data=='cb_gest_nomi_Zona3'):
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il NUOVO nome')
        msg=bot.send_message(cb.message.chat.id,'il nome attuale è ... '+cfgjsn['Zona3']+'. Inserisci il nuovo nome...' ,parse_mode='html',reply_markup=markup_force_reply,)
        bot.register_next_step_handler(msg, cambio_nome,'Zona3')
    elif(cb.data=='cb_gest_nomi_Zona4'):
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il NUOVO nome')
        msg=bot.send_message(cb.message.chat.id,'il nome attuale è ... '+cfgjsn['Zona4']+'. Inserisci il nuovo nome...' ,parse_mode='html',reply_markup=markup_force_reply,)
        bot.register_next_step_handler(msg, cambio_nome,'Zona4')
    elif(cb.data=='cb_gest_nomi_Zona5'):
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il NUOVO nome')
        msg=bot.send_message(cb.message.chat.id,'il nome attuale è ... '+cfgjsn['Zona5']+'. Inserisci il nuovo nome...' ,parse_mode='html',reply_markup=markup_force_reply,)
        bot.register_next_step_handler(msg, cambio_nome,'Zona5')
    elif(cb.data=='cb_gest_nomi_Zona6'):
        markup_force_reply=types.ForceReply(selective=False,input_field_placeholder='Inserisci il NUOVO nome')
        msg=bot.send_message(cb.message.chat.id,'il nome attuale è ... '+cfgjsn['Zona6']+'. Inserisci il nuovo nome...' ,parse_mode='html',reply_markup=markup_force_reply,)
        bot.register_next_step_handler(msg, cambio_nome,'Zona6')   

    # CallBack Funzioni Smart  
    elif(cb.data=='cb_funzioni_smart'):
        menu_smart(cb)
    # Smart Auto Inserimento
    elif(cb.data=='cb_smart_ai'):
        menu_smart_ai(cb)    
    elif(cb.data=='cb_smart_ai_attiva'):
        print ('Attivo il servizio di Auto Inserimento')
        log(nome + ' ha Abiliatato il servizio di Auto Inserimento' )
        scrivi_config(cb.message,'Auto_Ins','True')
        bot.send_message(cb.message.chat.id,"Ricordati di Abilitare almeno un utente alla gestione dell\' Auto Inserimento !")
    elif(cb.data=='cb_smart_ai_disattiva'):
        print ('Disattivo il servizio di Auto Inserimento')
        log(nome + ' ha Disabiliatato il servizio di Auto Inserimento' )
        scrivi_config(cb.message,'Auto_Ins','False')
    elif(cb.data=='cb_smart_ai_back'):
        menu_smart(cb)
    elif(cb.data=='cb_smart_ai_NO'):
        bot.send_message(cb.message.chat.id, "OK "+nome+" NON faccio nulla")
        menu_smart(cb)
    elif(cb.data=='cb_smart_ai_abilita'):    
        menu_smart_ai_abilita(cb)
    elif(cb.data=='cb_smart_ai_timer'):    
        menu_smart_ai_timer(cb)
    elif(cb.data=='cb_smart_ai_fo'):    
        menu_smart_ai_fascia_oraria(cb)
    # Smart Video Verifica        
    elif(cb.data=='cb_smart_video_ver'):
        menu_smart_video_ver(cb)
    elif(cb.data=='cb_smart_vv_abilita'):
        menu_smart_video_ver_abilita(cb)
    elif(cb.data=='cb_smart_vv_attiva'):
        print ('Attivo il servizio di Video Verifica')
        log(nome + ' ha Abiliatato il servizio di Video Verifica' )
        scrivi_config(cb.message,'Video','True')
    elif(cb.data=='cb_smart_vv_disattiva'):
        print ('Disattivo il servizio di Video Verifica')
        log(nome + ' ha Disabiliatato il servizio di Video Verifica' )
        scrivi_config(cb.message,'Video','False')   
    elif(cb.data=='cb_smart_vv_back'):
        menu_smart(cb)    
    elif(cb.data=='cb_smart_vv_NO'):
        bot.send_message(cb.message.chat.id, "OK "+nome+" NON faccio nulla")
        menu_smart(cb)
    elif(cb.data=='cb_smart_vv_link'):   
        menu_smart_vv_link(cb)
    elif(cb.data=='cb_smart_vv_link_1'):    
        menu_smart_vv_link_Z(cb,1)
    elif(cb.data=='cb_smart_vv_link_2'):    
        menu_smart_vv_link_Z(cb,2) 
    elif(cb.data=='cb_smart_vv_link_3'):    
        menu_smart_vv_link_Z(cb,3)    
    elif(cb.data=='cb_smart_vv_link_4'):    
        menu_smart_vv_link_Z(cb,4)
    elif(cb.data=='cb_smart_vv_link_5'):    
        menu_smart_vv_link_Z(cb,5) 
    elif(cb.data=='cb_smart_vv_link_6'):    
        menu_smart_vv_link_Z(cb,6)    
        
              
    # CallBck lettura Video
    elif(cb.data=='cb_video_webcam'):
        print (str(cb.message.chat.first_name))
        bot.send_message(cb.message.chat.id, 'Attendi mentre registro il video...')
        log(str(cb.message.chat.first_name) +' ha visualizzato il video della webcam')
        file_video=cattura_video(0)    
        bot.send_video(cb.message.chat.id,open(file_video, 'rb'),caption="Ecco il Video della webcam") 
    elif(cb.data=='cb_video_stream'):
        bot.send_message(cb.message.chat.id, 'Attendi mentre registro il video...')
        log(str(cb.message.chat.first_name)+' ha visualizzato il lo stream della ipcam')
        file_video=cattura_stream('rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4')    
        bot.send_video(cb.message.chat.id,open(file_video, 'rb'),caption="Ecco il Video dello stream")     
        
    # Callback Auto Inserimento
    elif(cb.data=='cb_ai_SI'):
        menu_inserisci(cb.message)
    elif(cb.data=='cb_ai_NO'):
        bot.send_message(cb.message.chat.id, '👍 '+nome+', NON Inserisco l\'Allarme.')
    elif(cb.data=='cb_ai_postponi'):
        bot.send_message(cb.message.chat.id, 'OK '+nome+' ti avviserò più tardi  😉')
        print ('Postponi --> ',time.asctime( time.localtime(time.time())))
        Timer_ai()
        
    # Callback ee
    elif(cb.data=='cb_ee_cav_si'):
        bot.send_message(cb.message.chat.id, 'TI CODDIDI !!! 🙈🙈🙈')
    elif(cb.data=='cb_ee_cav_NO'):
        bot.send_message(cb.message.chat.id, 'meno male 😱😱😱')
        

  
      
bot.add_custom_filter(custom_filters.TextMatchFilter())        
bot.add_custom_filter(CallbackFilter())       
bot.infinity_polling()

     

 



