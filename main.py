import datetime
import os
import pandas as pd
import numpy as np
import PySimpleGUI as sg
import database_df as db
import re
import glob
import subprocess
from checks import *
from chevron import *
import analysis as ana
from gui import *
import spotanalysis.constants as cs

### import data from database
Op, Roos, Semiflex, El = db.populate_fields()
currdatetime = datetime.datetime.today().strftime("%Y/%m/%d %H:%M:%S")
kpol, ndw, kelec, ks = db.update_cal(currdatetime,Roos,Semiflex,El)
kq=1.001
rbe=1.1
# Gantry specific reference data from database
ref_data = db.update_ref('DoseGy')
# Spot grid specific database labels
db_cols = cs.db_cols
# Spot grid energies from json file
cfg_dict = load_calibration()
spotE = cfg_dict['SpotE']
# Calibration data (kpol, ndw, kelec will update from database when Adate is generated)
selected_ks=None
selected_kpol=None
selected_kelec=None
selected_ndw=None

### Initialise session and results dicts
session = {}
# output consistency results
results = {}
results['Rindex']=[]
results['ADate']=[]
results['Energy']=[]
results['R']=[]
results['Ravg']=[]
results['Rrange prcnt']=[]
results['RGy']=[]
results['RavgGy']=[]
results['Rref']=[]
results['Rdelta']=[]
# chevron results
chev_results = {}
# spot grid results
spot_results = {}


### Helper function
# calculate output consistency values
def calc_metrics(i):
    '''
        Calculate mean dose from readings for energy layer i and update GUI display
        Input:
            i           int index of energy layer in GUI
        Return:
            r_mean      mean reading
            r_range     range betwen reading max-min
            d_mean      mean dose
            d_diff      percentage difference between mean reference dose values
            d           list of calculated dose values
    '''
    r = [float(x) for x in [values['r'+i+'1'],values['r'+i+'2']] if re.fullmatch(r'^(?:[0-9]+(?:\.[0-9]*)?)$', x)]
    r_mean=None
    r_range=None
    d = []
    d_mean=None
    d_diff=None
    diff_color='lightgray'
    if len(r)>0:
        # mean R
        r_mean = np.mean(r)
        window['rm'+i]('%.4f' % r_mean)
        # R range
        eps = np.finfo(float).eps # remove risk of dividing by zero
        r_range = (max(r)-min(r)) / (r_mean+eps) * 100
        window['rang'+i]('%.2f' % r_range)
        if len(window['rr'+i].get())>0:
            energy = int(window['E'+i].get())
            idx = ref_data['Energy'].index(energy)
            dref = ref_data[values['-G-']][idx]
            # Dose measured
            try:
                dose_coeff = tpc*float(selected_ndw)*float(kq)*float(selected_ks)*float(selected_kelec)*float(selected_kpol)*float(rbe)*1e-9
                # calc dose for each reading
                for reading in r:
                    d.append(reading*dose_coeff)
                # mean dose
                d_mean = np.mean(d)
                window['ad'+i]('%.4f' % d_mean)
                # Dose diff
                d_diff = (d_mean - dref)/dref*100
                # Conditional formatting
                if abs(d_diff)>=1.0:
                    diff_color='red'
                elif abs(d_diff)>=0.5:
                    diff_color='orange'
                else:
                    diff_color='green'
                window['diff'+i]('%.3f' % d_diff, background_color=diff_color, text_color='white')
            except:
                window['ad'+i]('')
                window['diff'+i]('', background_color=diff_color, text_color='black')
        
        return r_mean, r_range, d_mean, d_diff, d, r
    else:
        window['rm'+i].Update('')
        window['rang'+i]('')
        window['diff'+i]('',background_color=diff_color, text_color='black')
        window['ad'+i]('')


### Generate GUI
# dropdown list data
G = ['Gantry 1', 'Gantry 2', 'Gantry 3', 'Gantry 4']
Chtype = ['Roos', 'Semiflex']
V = [-400,-200,0,200,400]
Rng = ['Low','Medium','High']
Ch = Roos
en_layers = ['5']
layers = [[240,200,150,100,70]]
# create GUI window
window = build_window(Op, kq, rbe, El, G, Chtype, V, Rng, Ch, layers)
# GUI flags
tpc=None
session_analysed = False
export_flag=False
db_flag=False
# keyboard buttons move cursor in the GUI (up, down, enter)
window.bind('<Return>', '-NEXTE-') 
window.bind('<Down>', '-NEXT-')
window.bind('<Up>', '-PREV-')

### Event Loop listens out for GUI events e.g. button presses
while True:
    event, values = window.read()

    ### handle exit events
    if event == sg.WIN_CLOSED or event == 'Exit': ### user closes window or clicks cancel
        break

    ### clear fields on button press
    if event == '-NxtSess-':
        # deactivate buttons
        window['-Submit-'](disabled=True)
        window['-CSV_WRITE-'](disabled=True)
        # clear readings
        window['ADate'].Update('')
        window['GA'].Update('')
        window['-ML-'].Update('No comment')
        for i,E in enumerate(layers[0]):
            for r in range(1,3):
                window['r'+str(i)+str(r)].update('') 
            window['rm'+str(i)].update('') 
            window['rang'+str(i)].update('') 
            window['ad'+str(i)].update('') 
            window['diff'+str(i)].update('', background_color='light gray')  

    ### handle keyboard events
    if event == '-NEXT-':
        try:
            next_element = window.find_element_with_focus().get_next_focus()
            next_element.set_focus()
        except:
            "pass"
    if event == '-NEXTE-':
        try:
            next_element = window.find_element_with_focus().get_next_focus()
            next_element.set_focus()
        except:
            "pass"
    if event == '-PREV-':
        try:
            prev_element = window.find_element_with_focus().get_previous_focus()
            prev_element.set_focus()
        except:
            "pass"

    ### reset analysed flag if there is just about any event
    if event in window.key_dict.keys() and event not in ['-Submit-','-AnalyseS-','-Export-','-ML-','-NEXT-','-NEXTE-','-PREV-',sg.WIN_CLOSED]:
        session_analysed=False
        window['-CSV_WRITE-'](disabled=True) # disable csv export button
        window['-Submit-'](disabled=True) # disable access export button
        
    ### Button event actions
    if event == '-AnalyseS-': ### Analyse results 
        window['-AnalyseS-'](disabled=True)
        # initialise session integrity flag
        session_analysed=True       
        # output consistency session dict
        session = {}
        # output consistency results dict
        results = {}
        results['Rindex']=[]
        results['ADate']=[]
        results['Energy']=[]
        results['R']=[]
        results['Ravg']=[]
        results['Rrange prcnt']=[]
        results['RGy']=[]
        results['RavgGy']=[]
        results['Rref']=[]
        results['Rdelta']=[]

        # check data integrity
        print('Analysing...')
        anal_flag = pre_analysis_check(values, layers)
        if anal_flag[-1][0]:
            session_analysed = False
            print('ERROR: Session not analysed - check all information is entered correctly (Err Code: '+str(anal_flag[-1])+')')

        if session_analysed:
            try:
                ### POPULATE SESSION DICT
                session['Adate']=[values['ADate']]
                session['Op1']=[values['-Op1-']]
                session['Op2']=[values['-Op2-']]
                session['Temp']=[values['Temp']]
                session['P']=[values['Press']]
                session['Electrometer']=[values['-El-']]
                session['V']=[values['-V-']]
                session['Gantry']=[values['-G-']]
                session['GA']=[values['GA']]
                session['Chamber']=[values['-Ch-']]
                session['kQ']=[window['kq'].get()]
                session['ks']=[window['ks'].get()]
                session['kelec']=[window['kelec'].get()]
                session['kpol']=[window['kpol'].get()]
                session['NDW']=[window['ndw'].get()]
                session['TPC']=[str(tpc)]
                session['Humidity']=[values['H']]
                if len(values['-ML-'])<255:
                    session['Comments']=[values['-ML-']]
                else:
                    session['Comments']=[values['-ML-'][:255]]
            except:
                session_analysed = False
                print('ERROR: Session not analysed - check session data is complete')

        if session_analysed:
            try:
                ### POPULATE OUTPUT CONSISTENCY RESULTS DICT
                refs = [ref_data[values['-G-']],ref_data['Energy']]
                tstamp = values['ADate']
                cnt=0
                for i,_ in enumerate(layers[0]):
                    if window['diff'+str(i)].get() != '':
                        en = int(window['E'+str(i)].get())
                        idx = refs[1].index(en)
                        r_mean, r_range, d_mean, d_diff, d, r = calc_metrics(str(i))
                        for j, (rn, dn) in enumerate(zip(r,d)):
                            cnt += 1
                            #results['Rindex'].append("%02d_%01d"%(i,j))
                            results['Rindex'].append(str(cnt))
                            results['ADate'].append(values['ADate'])
                            results['Energy'].append(window['E'+str(i)].get())
                            results['R'].append(str(rn))
                            results['Ravg'].append(str(r_mean))
                            results['Rrange prcnt'].append(str(r_range))
                            results['RGy'].append(str(dn))
                            results['RavgGy'].append(str(d_mean))
                            results['Rref'].append(str(refs[0][idx]))
                            results['Rdelta'].append(str(d_diff))
            except:
                session_analysed = False
                print('ERROR: Results not analysed - check all information is entered correctly')
                sg.popup("Session not analysed","Check you have entered all information correctly")

        if len(results['R'])==0 and session_analysed:
            # Catch if no output measurements have been recorded
            session_analysed = False
            print('ERROR: Session not analysed - check output measurements')
            sg.popup("No Results","Enter some results before clicking Check Session")


        ### LOGOS ANALYSIS
        if not os.path.isdir(values['-Logos-']):
            session_analysed = False
            print('ERROR: Selected Logos directory does not exist')
            sg.popup("Invalid directory","Select a folder containing valid Logos data")

        if session_analysed:
            logos_dir=values['-Logos-']
            try:
                ### CHEVRON and SPOT GRID FOLDER SORTING
                chevron_dir, spot_dirs, report_dir = \
                    ana.organise_logos_dirs(values)
            except:
                session_analysed = False
                print('ERROR: Results not analysed - check Logos data')
                sg.popup("No Results","Enter path to valid Logos data before clicking Check Session")

        if session_analysed:
            try:
                ### CHEVRON DATA ANALYSIS
                chev_results = ana.chevron_results(chevron_dir, values)
            except:
                session_analysed = False
                print('ERROR: Chevron results')
                sg.popup("No Chevron Results","Unable to process Chevron data, check Logos files")
        
        if session_analysed:
            try:
                ### SPOT GRID DATA ANALYSIS
                df_spot, device, spotpatterns, all_data = ana.spot_results(spot_dirs, spotE, values, cs.db_cols)
            except:
                session_analysed = False
                print('ERROR: Spot grid results')
                sg.popup("No Spot Grid Results","Unable to process Spot Grid data, check Logos files")

        if session_analysed:
            try:
                ### GENERATE REPORT PDFs
                ana.spot_report(df_spot, device, report_dir, values, spotE)
                ana.chev_report(chev_results, values, 1.0, 0.5, os.path.join(report_dir,'02_chevron_report.pdf'))
                report_results = ana.output_results(results)
                ana.output_report(report_results, values, 1.0, 0.5, os.path.join(report_dir,'01_output_report.pdf'))
                pdf_list = glob.glob(os.path.join(report_dir,'*.pdf'))
                pdf_list.sort()
                report_name = os.path.join(report_dir,'PostISM_Report.pdf')
                ana.merge_reports(pdf_list, report_name)
            except:
                session_analysed = False
                print('ERROR: Reports not generated')
                sg.popup("Reports not generated","Reports could not be generated, check config files and dependencies")


        if session_analysed:
            #activate buttons
            window['-CSV_WRITE-'](disabled=False)
            window['-Submit-'](disabled=False)
            # convert session and results to dataframes
            sess_df = pd.DataFrame.from_dict(session)
            reslt_df = pd.DataFrame.from_dict(
                {k: results[k] for k in results.keys() & {'Rindex', 'ADate', 'Energy', 'R', 'RGy'}}
                )
            reslt_df = reslt_df[['Rindex','ADate','Energy','R','RGy']]
            chev_reslt_df = pd.DataFrame.from_dict(
                {k: chev_results[k] for k in chev_results.keys() & {'Energy MeV','D80 mm', 'Diff TPS mm', 'Diff NIST mm', 'Diff Baseline mm'}}
                )
            chev_reslt_df['ADate']=values['ADate']
            chev_reslt_df = chev_reslt_df[['ADate','Energy MeV','D80 mm', 'Diff TPS mm', 'Diff NIST mm', 'Diff Baseline mm']]
            
        if os.path.isdir(values['-Logos-']) and session_analysed:
            db.review_dose(sess_df,reslt_df,values['-Logos-'])
            db.review_range(chev_results)
            print('Results analysed.')
        else:
            #deactivate buttons
            window['-CSV_WRITE-'](disabled=True)
            window['-Submit-'](disabled=True)
        window['-AnalyseS-'](disabled=False)

        if session_analysed:
            try:
                subprocess.Popen([report_name],shell=True)
            except:
                print('WARNING: Report could not be opened')
                sg.popup("Report not displayed","Report could not be displayed, manually inspect the file:\n"+report_name)

                
    if event == '-Export-': ### Export results to csv
        print('Exporting to csv...')
        export_flag=False
        try:
            # create timestamped folder
            csv_time = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            csv_dir = values['-Export-']+os.sep+csv_time+'_'+values['-G-']
            os.makedirs(csv_dir, exist_ok=True)
            sess_df.to_csv(csv_dir+os.sep+'session.csv', index=False)
            reslt_df.to_csv(csv_dir+os.sep+'result.csv', index=False)
            print('Exported.')
            export_flag=True
        except:
            print('ERROR: Failed to export to csv!')
        if export_flag:
            #deactivate buttons
            window['-Submit-'](disabled=False)
        else:
            window['-Submit-'](disabled=True)


    if event == '-Submit-': ### Submit data to database
        db_flag=True
        try:
            # write output cons session and results to db
            sess_cols = 'ADate,[Op1],[Op2],[T],[P],Electrometer,[V],MachineName,GA,Chamber,kQ,ks,kelec,kpol,NDW,TPC,Humidity,Comments'
            res_cols = 'Rindex,ADate,Energy,[R],RGy'
            db.write_to_db(sess_df,
                           reslt_df,
                           'LogosOPSession',
                           'LogosOPResults',
                           sess_cols,
                           res_cols)
        except:
            print('outputs failed to write to DB')
            db_flag=False

        try:
            # write chevron results to db
            sess_cols = 'ADate,[Op1],[Op2],MachineName,GA,Comments'
            res_cols = 'ADate,Energy,[D80],DiffTPS,DiffNIST,DiffBaseline'
            db.write_to_db(sess_df[['Adate','Op1','Op2','Gantry','GA','Comments']],
                           chev_reslt_df,
                           'ChevronSession',
                           'ChevronResults',
                           sess_cols,
                           res_cols)
        except:
            print('chevrons failed to write to DB')
            db_flag=False
        
        try:
            # write spot grid results to db
            db.spots_to_db(all_data, spotpatterns, values)
        except:
            print ('spot grids failed to write to DB')
            db_flag=False

        if db_flag:
            #deactivate buttons
            print('######### All results written to Database #########')
            window['-Submit-'](disabled=True)
            window['ADate'].Update('')
            values['ADate']=''
            window['-ML-'].Update('No comment')
        else:
            window['-CSV_WRITE-'](disabled=True)
            window['-Submit-'](disabled=True)


    ### Populate Chamber ID list
    if event == '-Chtype-':   # chamber type dictates chamber list
        if values['-Chtype-'] == 'Roos':
            Ch = Roos
        elif values['-Chtype-'] == 'Semiflex':
            Ch = Semiflex
        else:
            Ch = []
        window['-Ch-'].update(values=Ch, value='') # update Ch combo box
    
    ### Update calibration factors on Date change
    if event == 'ADate':
        try:
            kpol, ndw, kelec, ks = db.update_cal(values['ADate'],Roos,Semiflex,El)
        except:
            pass
        
        if values['-G-'] in G:
            selected_ks=ks[values['-G-']]
            window['ks'](str(selected_ks))
        else:
            window['ks']('')
        
        if values['-Chtype-'] == 'Roos':
            Ch = Roos
        elif values['-Chtype-'] == 'Semiflex':
            Ch = Semiflex
        else:
            Ch = []
        window['-Ch-'].update(values=Ch, value='') # update Ch combo box

        if values['-El-'] in El:
            selected_kelec=kelec[values['-El-']]
            window['kelec'](str(selected_kelec)) 
        else:
            window['kelec']('') 

        if values['-Ch-'] in Ch:
            selected_ndw = ndw[values['-Ch-']]
            selected_kpol = kpol[values['-Ch-']]
            window['kq'](str(kq)) 
            window['kpol'](str(selected_kpol))
            window['ndw'](str(selected_ndw)) 
        else:
            window['kq']('') 
            window['kpol']('')
            window['ndw']('') 

        for i,_ in enumerate(layers[0]):
            _=calc_metrics(str(i))

    ### Update calibration factors on Gantry, Chamber & Electrometer changes
    if event == '-G-':
        selected_ks = ks[values['-G-']]
        window['ks'](str(selected_ks)) 
        for i,_ in enumerate(layers[0]):
            _=calc_metrics(str(i))
    
    if event == '-Ch-':
        if values['-Ch-'] in Ch:
            selected_ndw = ndw[values['-Ch-']]
            selected_kpol = kpol[values['-Ch-']]
            window['kq'](str(kq)) 
            window['kpol'](str(selected_kpol))
            window['ndw'](str(selected_ndw)) 
        else:
            window['kq']('') 
            window['kpol']('')
            window['ndw']('') 
        for i,_ in enumerate(layers[0]):
            _=calc_metrics(str(i))

    if event == '-El-':
        if values['-El-'] in El:
            selected_kelec=kelec[values['-El-']]
            window['kelec'](str(selected_kelec)) 
        else:
            window['kelec']('') 
        for i,_ in enumerate(layers[0]):
            _=calc_metrics(str(i))

    ### Update temp and press correction
    if event in ['Temp','Press'] and re.match('[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)', values[event]):
        try:
            t = float(values['Temp'])
            p = float(values['Press'])
            tpc = (t+273.15)/293.15*1013.25/p
            window['tpc']('%.4f' % tpc)
            for i,_ in enumerate(layers[0]):
                _=calc_metrics(str(i))
        except:
            window['tpc']('')
    
    ### Update reference values
    if event == '-G-' and values['-G-'] in G:
        refs = [ref_data[values['-G-']],ref_data['Energy']]
        for i,_ in enumerate(layers[0]):
            if window['E'+str(i)].get() != '':
                en = int(window['E'+str(i)].get())
                idx = refs[1].index(en)
                window['rr'+str(i)].update("%.4f" % refs[0][idx])
            _=calc_metrics(str(i))

    ### Calculate average, diff, range and dose on the fly
    if event in ['r'+str(i)+str(j) for i,_ in enumerate(layers[0]) for j in range(1,3)] and \
        (re.match('[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)', values[event]) or values[event]==''):      
        i = event[1:-1]
        _ = calc_metrics(i)
