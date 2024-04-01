
import datetime
#import time
import os
#from turtle import color
import pandas as pd
import numpy as np
import PySimpleGUI as sg
import database_df as db
import re
from checks import *
from chevron import *

### GUI window function
def build_window(Op, kq, rbe, El, G, Chtype, V, Rng, Ch, layers):
    '''
        Create the GUI layout
        Returns PySimpleGUI window object
    '''
    #theme
    sg.theme('DefaultNoMoreNagging')

    #equipment
    sess0_layout = [
        [sg.T('Date', justification='right', size=(5,1)), sg.Input(key='ADate', enable_events=True, size=(18,1), readonly=True)],
        [sg.T('', size=(5,1)), sg.CalendarButton('yyyy/mm/dd hh:mm:ss', font=('size',9), target='ADate',format='%Y/%m/%d %H:%M:%S', close_when_date_chosen=True, no_titlebar=False, key='-CalB-')],
    ]
    sess1_layout = [
        [sg.T('Operator 1', justification='right', size=(13,1)), sg.DD(['']+Op, size=(8,1), key='-Op1-', readonly=True)],
        [sg.T('Operator 2', justification='right', size=(13,1)), sg.DD(['']+Op, size=(8,1), key='-Op2-', readonly=True)],
    ]

    #calibration
    cal0_layout = [
        [sg.T('T (C)', justification='right', size=(8,1)), sg.Input(key='Temp', enable_events=True, size=(6,1))],
        [sg.T('P (hPa)', justification='right', size=(8,1)), sg.Input(key='Press', enable_events=True, size=(6,1))],
        [sg.T('TPC', justification='right', size=(8,1)), sg.T(key='tpc', size=(6,1), background_color='lightgray', text_color='black', justification='right')],
    ]
    cal1_layout = [
        [sg.T('kQ', justification='right', size=(5,1)), sg.T(str(kq), key='kq', size=(5,1), background_color='lightgray', text_color='black', justification='right')],
        [sg.T('ks', justification='right', size=(5,1)), sg.T(key='ks', enable_events=True, size=(5,1), background_color='lightgray', text_color='black', justification='right')],
        [sg.T('kelec', justification='right', size=(5,1)), sg.T(key='kelec', enable_events=True, size=(5,1), background_color='lightgray', text_color='black', justification='right')],
    ]
    cal3_layout = [
        [sg.T('kpol', justification='right', size=(5,1)), sg.T(key='kpol', enable_events=True, size=(5,1), background_color='lightgray', text_color='black', justification='right')],
        [sg.T('RBE', justification='right', size=(5,1)), sg.T(str(rbe), key='rbe', enable_events=True, size=(5,1), background_color='lightgray', text_color='black', justification='right')],
        [sg.T('Ndw', justification='right', size=(5,1)), sg.T(key='ndw', enable_events=True, size=(8,1), background_color='lightgray', text_color='black', justification='right')],
    ]
    cal4_layout = [
        [sg.T('H (%)', justification='right', size=(5,1)), sg.Input(key='H', enable_events=True, size=(12,1))],
    ]

    #equipment
    eq0_layout = [
        [sg.T('Gantry', justification='right', size=(12,1)), sg.DD(G, size=(11,1), enable_events=True, key='-G-', readonly=True)],
        [sg.T('GA (deg)', justification='right', size=(12,1)), sg.Input(key='GA', enable_events=True, default_text='0', size=(11,1))],
    ]
    eq1_layout = [
        [sg.T('Chamber Type', justification='right', size=(12,1)), sg.DD(Chtype, size=(11,1), default_value='Roos', enable_events=True, key='-Chtype-', readonly=True)],
        [sg.T('Chamber', justification='right', size=(12,1)), sg.DD(Ch, size=(11,1), enable_events=True, key='-Ch-', readonly=True)],
    ]
    eq2_layout = [
        [sg.T('Electrometer', justification='right', size=(12,1)), sg.DD(El, size=(11,1), enable_events=True, key='-El-', readonly=True)],
        [sg.T('Voltage (V)', justification='right', size=(12,1)), sg.DD(V, size=(11,1), enable_events=True, key='-V-', readonly=True)],
    ]

    #Roos results
    def results_fields(layers=layers[0], Rng=Rng):
        en_layout = [ [sg.T('Energy (MeV):')] ]
        el_layout = [ [sg.T('Range:')] ]
        r1_layout = [ [sg.T('R1 (nC):')] ]
        r2_layout = [ [sg.T('R2 (nC):')] ]
        r3_layout = [ [sg.T('R3 (nC):')] ]
        r4_layout = [ [sg.T('R4 (nC):')] ]
        r5_layout = [ [sg.T('R5 (nC):')] ]
        rm_layout = [ [sg.T('Ravg (nC):')] ]
        rr_layout = [ [sg.T('Dref (Gy):')] ]
        diff_layout = [ [sg.T('Ddiff (%):')] ]
        rang_layout = [ [sg.T('Rrng (%):')] ]
        ad_layout = [ [sg.T('Davg (Gy):')] ]
        for i,E in enumerate(layers):
            en_layout.append([sg.T(str(E), size=(10,1), justification='right', key='E'+str(i), visible=True)])
            el_layout.append([sg.DD(Rng, size=(8,1), default_value=Rng[1], enable_events=True, key='-Rng'+str(i)+'-', readonly=True)])
            r1_layout.append([sg.InputText(key='r'+str(i)+'1', default_text='', size=(6,1), justification='right', enable_events=True)])
            r2_layout.append([sg.InputText(key='r'+str(i)+'2', default_text='', size=(6,1), justification='right', enable_events=True)])
            rm_layout.append([sg.T('', background_color='lightgray', text_color='black', justification='right',  key='rm'+str(i), size=(6,1))])
            rr_layout.append([sg.T('', background_color='lightgray', text_color='black', justification='right',  key='rr'+str(i), size=(6,1))])
            diff_layout.append([sg.T('', background_color='lightgray', text_color='black', justification='right',  key='diff'+str(i), size=(6,1))])
            rang_layout.append([sg.T('', background_color='lightgray', text_color='black', justification='right',  key='rang'+str(i), size=(6,1))])
            ad_layout.append([sg.T('', background_color='lightgray', text_color='black', justification='right',  key='ad'+str(i), size=(6,1))])
        measurements_layout = sg.Frame('Output Consistency',
                                [[  sg.Column(en_layout),
                                    sg.Column(el_layout),
                                    sg.Column(r1_layout),
                                    sg.Column(r2_layout),
                                    sg.Column(rm_layout),
                                    sg.Column(rang_layout),
                                    sg.Column(ad_layout),
                                    sg.Column(rr_layout),
                                    sg.Column(diff_layout)  ]],
                                key='-Measurements-')
        return measurements_layout
    
    # Chevron
    fb_layout = [
        [sg.FolderBrowse('Select Logos Data', key='-LogosBrowse-', disabled=False, target='-Logos-'), sg.In(key='-Logos-', enable_events=True, visible=True)],
    ]

    # Comments
    ml_layout = [
        [sg.Multiline('Post-ISM', key='-ML-', enable_events=True, size=(120,3))],
    ]

    #buttons
    button_layout = [
        [sg.B('Check Session', key='-AnalyseS-'),
         sg.B('Submit to Database', disabled=True, key='-Submit-'),
         sg.FolderBrowse('Export to CSV', key='-CSV_WRITE-', disabled=True, target='-Export-', visible=False), sg.In(key='-Export-', enable_events=True, visible=False),
         sg.B('Clear Results', button_color='red', key='-NxtSess-'),
         sg.ProgressBar(max_value=10, orientation='h', size=(48, 20), key='progress')],
    ]

    #combine layout elements
    layout = [
        [sg.Text('OGrE Checks:', font=['bold',18])],
        [sg.Frame('Session',[[sg.Column(sess0_layout), sg.Column(sess1_layout)]], size=(420,110)),
         sg.Frame('Calibration',[[sg.Column(cal0_layout), sg.Column(cal1_layout), sg.Column(cal3_layout)]], size=(420,110))],
        [sg.Frame('Equipment',[[sg.Column(eq0_layout), sg.Column(eq1_layout), sg.Column(eq2_layout)]], size=(688,80)), sg.Frame('Humidity',[[sg.Column(cal4_layout)]], size=(110,80))],
        [results_fields()],
        [sg.Frame('Logos', fb_layout)],
        [sg.Frame('Comments', ml_layout)],
        [button_layout],
    ]

    icon_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'icon', 'cat.ico'))
    return sg.Window('OGrE Checks', layout, resizable=False, finalize=True, grab_anywhere=True, return_keyboard_events=True, icon=icon_file)