"""
Created on Thurs May 26 2022
@author: Alex Grimwood
Interaction with QA database
"""

import re
import os
import sys
import PySimpleGUI as sg
import pypyodbc
from pypyodbc import IntegrityError
import pandas as pd
import matplotlib
import matplotlib.figure as figure
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FormatStrFormatter
from PIL import ImageGrab
import seaborn as sns
import configparser
import datetime
matplotlib.use('TkAgg')


cfg = os.path.abspath(os.path.join(os.path.dirname(__file__), 'db_config.cfg'))
config = configparser.ConfigParser()
config.readfp(open(file=cfg))
SESSION_TABLE = config.get('DB_DETAILS','SESSION_TABLE')
RESULTS_TABLE = config.get('DB_DETAILS','RESULTS_TABLE')
DB_PATH = config.get('DB_DETAILS','DB_PATH')
PASSWORD = config.get('DB_DETAILS','PASSWORD')

def populate_fields():
    '''
        Populate dropdown boxes from database
        return:
            Op          list of operator initials
            Roos        list of Roos chamber serials
            Semiflex    list of semiflex serials
            El          list of electrrometer serials
    '''
    print("Connecting to database...")
    connection_flag = True
    # operators list
    fields = {'table': 'Operators', 'target': 'Initials', 'filter_var': None}
    Op = read_db_data(fields)
    if not Op:
        print("Operator initials could not be retrieved from database!")
        Op = ['AB', 'AG', 'AGr', 'AJP', 'AK', 'AM', 'AT', 'AW', 'CB', 'CG', 'LHC', 'PI', 'RM', 'SC', 'SG', 'SavC', 'TNC', 'VMA', 'VR']
        connection_flag = False
    Op.sort()
    # chamber list
    fields = {'table': 'Assets', 'target': "[Serial Number]", 'filter_var': "Model", 'filter_val': 'TW34001SC'}
    Roos = read_db_data(fields)
    if not Roos:
        print("Roos serial numbers could not be retrieved from database!")
        Roos = ['003126', '003128', '003131', '003132']
        connection_flag = False
    else:
        Roos = [str(int(i)) for i in Roos]
    fields['filter_val'] = 'TW31021'
    Semiflex = read_db_data(fields)
    if not Semiflex:
        print("Semiflex serial numbers could not be retrieved from database!")
        Semiflex = ['142438', '142586', '142587']
        connection_flag = False
    # electrometer list
    fields['filter_val'] = 'UnidosE'
    El = read_db_data(fields)
    if not El:
        print("Electrometer serial numbers could not be retrieved from database!")
        El = ['92579', '92580', '92581']
        connection_flag = False
    if connection_flag:
        print("Connected...")
    return Op, Roos, Semiflex, El


def update_ref(valtype):
    '''
        Create a dictionary ref_data of most recent reference dose values
        in OutputConsRef table.

        list of reference dose energies:
            ref_data['Energy']

        lists of reference doses:
            ref_data['Gantry 1']
            ref_data['Gantry 2']
            ref_data['Gantry 3']
            ref_data['Gantry 4']
    '''
    # instantiate reference data
    e_lst = list(range(240,69,-10))
    ref_data = {'Energy': e_lst,
        'Gantry 1': [0]*len(e_lst),
        'Gantry 2': [0]*len(e_lst),
        'Gantry 3': [0]*len(e_lst),
        'Gantry 4': [0]*len(e_lst),
        }
    # connect to DB
    conn=None
    if not DB_PATH:
        sg.popup("Path Error.","Provide a path to the Access Database.")
        print("Database Path Missing!")
        return None
    if PASSWORD:
        new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;PWD=%s'%(DB_PATH,PASSWORD) 
    else:
        new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s'%(DB_PATH)   
    try:  
        conn = pypyodbc.connect(new_connection)               
    except:
        print("Connection to QA database failed...")
        sg.popup("Could not connect to database","WARNING")
    if isinstance(conn,pypyodbc.Connection):
        # retrieve most recent reference data from DB
        sql =   '''
                    Select A.Energy, A.MachineName, A.RefVal 
                    From (  Select Energy
                            , MachineName
                            , RefVal
                            , RefDate
                            , RefType
                            From LogosRef Where RefType = '%s'
                        ) As A
                    Inner Join (
                                Select Energy
                                , MachineName
                                , RefType
                                , Max(RefDate) As MRefDate
                                From LogosRef
                                Group By Energy, MachineName, RefType
                                ) As B
                    On A.Energy = B.Energy
                    And A.MachineName = B.MachineName
                    And A.RefType = B.RefType
                    And A.RefDate = B.MRefDate
                ''' %(valtype)
        cursor = conn.cursor()
        cursor.execute(sql)
        records = cursor.fetchall()
        cursor.close()
        conn.commit()
        conn = None        
        #write to dict
        for row in records:
            en = row[0]
            machine = row[1]
            refdose = row[2]
            if en in e_lst:
                idx = e_lst.index(en)
                ref_data[machine][idx]=refdose
    return ref_data


def update_cal(Adate,roos,semiflex,elect):
    '''
        Retrieve valid calibration factors from database
        Input:
            Adate       string timestamp in the format dd/mm/yyyy hh:mm:ss
            roos        list of roos serial numbers
            semiflex    list of semiflex serial numbers
            elect       list of electrometer serial numbers

        Return int values for:
            kpol
            ndw
            kelec
    '''
    # concatenate all serial numbers
    roos = [str(int(i)) for i in roos]
    ch_numbers = roos + semiflex

    # instantiate cal factor dicts
    kpol = {}
    ndw = {}
    kelec = {}
    if Adate=='':
        sg.popup("Date required","Please enter a date to retrieve the latest calibration factors.")
        return False
    else:
        # reformat date
        y = Adate[0:4]
        m = Adate[5:7]
        d = Adate[8:10]
        #query_date = y+'-'+m+'-'+d
        query_date = "'%s-%s-%s'"%(y,m,d)
        # query database for most recent calibration factors
        sql = '''SELECT CQ2.*, Assets.Category \
            FROM Assets INNER JOIN \
            (SELECT Calibration.Equipment, Calibration.[CalFactor], Calibration.Kpol, Calibration.[Cal Date] \
            FROM (SELECT A.[Equipment], Max(A.[Cal Date]) AS [MaxOfCal Date] \
            FROM Calibration AS A WHERE A.[Cal Date] <= CDate(%s) \
            GROUP BY A.[Equipment])  AS CQ1 INNER JOIN Calibration \
            ON (CQ1.[MaxOfCal Date] = Calibration.[Cal Date]) AND (CQ1.Equipment = Calibration.Equipment) \
            WHERE ((Calibration.Operator) Is Not Null))  AS CQ2 ON Assets.Item = CQ2.Equipment;'''%(query_date)
        try:
            new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;PWD=%s'%(DB_PATH,PASSWORD) 
            conn = pypyodbc.connect(new_connection) 
        except:
            return 1,1,1,1
         
        cursor = conn.cursor()
        cursor.execute(sql)
        records = cursor.fetchall()
        cursor.close()
        conn.commit()
        #conn = None
        # cal factors to dicts
        for k in records:
            for x in ch_numbers:
                if "["+x+"]" in k[0]:
                    ndw[x]=int(k[1])
                    kpol[x]=int(k[2])
            for y in elect:
                if "["+y+"]" in k[0]:
                    kelec[y]=int(k[1])

        # query database for most recent gantry-specific cal factors
        sql = '''
                SELECT
                    Outputcons_ks.MachineName, Outputcons_ks.CorrFactorVal
                FROM
                    (   SELECT
                        MachineName, Max(CalDate) AS MCalD
                        FROM
                        Outputcons_ks
                        GROUP BY
                        MachineName) AS B
                INNER JOIN
                    Outputcons_ks
                ON
                    Outputcons_ks.MachineName = B.MachineName AND
                    Outputcons_ks.CalDate = B.MCalD
                WHERE
                    Outputcons_ks.CorrFactor = 'ks'
            '''
        cursor = conn.cursor()
        cursor.execute(sql)
        records = cursor.fetchall()
        cursor.close()
        conn.commit()
        conn = None
        ks = dict(records)
        return kpol, ndw, kelec, ks


def review_dose(session_df=pd.DataFrame(), results_df=pd.DataFrame(), png_dir=None):
    '''
        Function returns a DB table of historic dose measurements.
        Pulls all readings for the sesison's gantry and angle

        Input:
            session_df  -   session dataframe generated by GUI in main.py
            results_df  -   results dataframe generated by GUI in main.py
        
        Output:
            A new window showing historic measurements as a heatmap (x-axis: date, y-axis: energy)
    '''
    if session_df.empty or results_df.empty:
        return
    
    # retrieve current session's data
    query_gantry = session_df['Gantry'][0]
    dfrec = pd.DataFrame()
    dfrec['Energy']=results_df['Energy'].astype(int)
    dfrec['RGy']=results_df['RGy'].astype(float)
    dfrec['ADate']=[pd.to_datetime(session_df['Adate'][0], format='%Y/%m/%d %H:%M:%S') for x in range(len(dfrec.index))]

    # retrieve previous Logos session's data
    # Append to current session's data
    # consider finding group average dose across readings (df.groupby ADate Energy mean RGy)

    # retireve reference readings and join onto dataframe
    sql =   '''
                Select A.Energy, A.RefVal 
                    From (  Select Energy
                            , MachineName
                            , RefVal
                            , RefDate
                            , RefType
                            From LogosRef Where RefType = 'DoseGy'
                        ) As A
                    Inner Join (
                                Select Energy
                                , MachineName
                                , RefType
                                , Max(RefDate) As MRefDate
                                From LogosRef
                                Group By Energy, MachineName, RefType
                                ) As B
                    On A.Energy = B.Energy
                    And A.MachineName = B.MachineName
                    And A.RefType = B.RefType
                    And A.RefDate = B.MRefDate
                    WHERE  A.MachineName = '%s'
            '''%(query_gantry)
    
    new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;PWD=%s'%(DB_PATH,PASSWORD)   
    try:
        conn = pypyodbc.connect(new_connection)
        cursor = conn.cursor()
        cursor.execute(sql)
    except:
        sg.popup("Database Could Not Be Read","Check nobody is viewing the database and try again.")
        return
    records = cursor.fetchall()
    if len(records)==0:
        sg.popup("No Database Matches","No records in database match the equipment specified for this session")
        return
    cursor = conn.cursor()
    cursor.execute(sql)
    records = cursor.fetchall()
    cursor.close()
    conn.commit()
    cols = ['Energy','RefGy']
    df_ref = pd.DataFrame(list(records), columns=cols)
    dfrec['ADate']=[pd.to_datetime(session_df['Adate'][0], format='%Y/%m/%d %H:%M:%S') for x in range(len(dfrec.index))]
    dfrec = dfrec.join(df_ref.set_index('Energy'), on='Energy')
    dfrec['Diff (%)'] = (dfrec['RGy'].astype(float)-dfrec['RefGy'])/dfrec['RefGy']*100 # calculate percent diff from ref
    
    # retrieve historic readings from database
    query_angle = session_df['GA'][0]  
    y = session_df['Adate'][0][0:4]
    m = session_df['Adate'][0][5:7]
    d = session_df['Adate'][0][8:10]
    query_date = "%s-%s-%s"%(int(y)-1,m,d) #confine historic record to previous 12 months
    query_date2 = "%s-%s-%s"%(y,m,int(d))  
    sql =   '''
            SELECT  A.Adate
                , A.[MachineName]
                , A.[GA]
                , A.[kQ]
                , A.[ks]
                , A.[kelec]
                , A.[kpol]
                , A.[NDW]
                , A.[TPC]
                , B.Energy
                , B.[R]
            FROM OutputConsSession A
            INNER JOIN OutputConsResults B
            ON A.Adate = B.ADate
            WHERE A.[MachineName] LIKE '%%%s%%'
            AND A.[GA]= %s
            AND (A.Adate BETWEEN #%s# AND #%s#)
            '''%(query_gantry, query_angle, query_date, query_date2)

    cursor = conn.cursor()
    cursor.execute(sql)
    records = cursor.fetchall()
    cursor.close()
    conn.commit()
    G = records[0][1]
    GA = str(int(records[0][2])) 
    cols = [
        'ADate',
        'MachineName',
        'GA',
        'kQ',
        'ks',
        'kelec',
        'kpol',
        'NDW',
        'TPC',
        'Energy',
        'R'
    ]
    df = pd.DataFrame(list(records), columns=cols)
    df['RGy'] = df['R'] * df['kelec']*df['TPC']*df['ks']*df['NDW']*df['kpol']*df['kQ']*1.1/1000000000
    df[['ADate','Energy','RGy']]

    # retireve reference readings and join onto dataframe
    sql =   '''
                Select A.Energy, A.RefDose
                From OutputConsRef As A
                Inner Join (
                            Select Energy, MachineName, Max(RefDate) As MRefDate
                            From OutputConsRef
                            Group By Energy, MachineName) As B
                On A.Energy = B.Energy
                And A.MachineName = B.MachineName
                And A.RefDate = B.MRefDate
                WHERE  A.MachineName = '%s'
            '''%(query_gantry)

    cursor = conn.cursor()
    cursor.execute(sql)
    records = cursor.fetchall()
    cursor.close()
    conn.commit()
    conn = None
    cols = ['Energy','RefGy']
    df_ref = pd.DataFrame(list(records), columns=cols)
    df = df.join(df_ref.set_index('Energy'), on='Energy')
    df['Diff (%)'] = (df['RGy'].astype(float)-df['RefGy'])/df['RefGy']*100 # calculate percent diff from ref
    df = pd.concat([df, dfrec])
    df['ADate'] = df['ADate'].dt.floor('1d')
    df['ADate'] = df['ADate'].dt.strftime('%Y/%m/%d')

    # plot the output consistency results in a new window
    vmax = max([abs(df['Diff (%)'].min()),abs(df['Diff (%)'].max())])
    vmin = vmax*-1
    df = df.pivot_table(index="Energy",columns="ADate",values="Diff (%)", aggfunc="mean")
    cmap = 'vlag'
    size_x = 500
    size_y = 700
    fig, axes = plt.subplots(1,2,
                           gridspec_kw={'height_ratios':[1],
                                  'width_ratios' :[1,0.01]},
                            constrained_layout=True)
    DPI = fig.get_dpi()
    fig.set_size_inches(size_x * 2 / float(DPI), size_y / float(DPI))
    sns.heatmap(df, cmap=cmap, square=False, 
                ax=axes[0],
                cbar_ax=axes[1],
                vmax=vmax,
                vmin=vmin)
    axes[1].yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
    axes[1].yaxis.tick_left()
    plt.sca(axes[1])    
    plt.yticks(fontsize=6)
    plt.ylabel("Difference From Dose Ref (%)", fontsize=10)
    ax=axes[0]
    ax.invert_yaxis()
    plt.sca(ax)
    plt.xlabel("Date (YYYY/MM/DD)", fontsize=8)
    plt.xticks(rotation=45, ha='right', fontsize=6)
    plt.ylabel("Energy (MeV)", fontsize=8)
    plt.yticks(fontsize=6)
    plt.title(G+" Outputs at GA"+GA, fontsize=10)

    if os.path.isdir(png_dir):
        fig.savefig(os.path.join('output_heatmap.png'))

    # generate heatmap in popup window
    layout = [
        [sg.Canvas(key='controls_cv')],
        [sg.Column(
            layout=[[sg.Canvas(key='-CANVAS-', size=(size_x * 2, size_y))]],
            background_color='#DAE0E6',
            pad=(0, 0)
            )
        ],
    ]
    window = sg.Window("OUTPUT CONSISTENCY RESULTS", layout, modal=True, finalize=True)
    choice = None
    while True:
        fig_canvas_agg = _draw_figure(window['-CANVAS-'].TKCanvas, fig)
        event, values = window.read()
        if event == "Exit" or event == sg.WIN_CLOSED:
            break
        
    window.close()
    return None


def _draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg


def save_element_as_file(element, filename):
    """
    Saves any PySimpleGUI element as an image file.  Element needs to have an underlyiong Widget available (almost if not all of them do)
    :param element: The element to save
    :param filename: The filename to save to. The extension of the filename determines the format (jpg, png, gif, ?)
    """
    widget = element.Widget
    box = (widget.winfo_rootx(), widget.winfo_rooty(), widget.winfo_rootx() + widget.winfo_width(), widget.winfo_rooty() + widget.winfo_height())
    grab = ImageGrab.grab(bbox=box)
    grab.save(filename)


# generate chevron results window
def review_range(chev_results=None, png_file=None, fail_threshold=1.0, warn_threshold=0.5):
    row_titles = ['Energy', 'D80 mm', 'TPS delta mm', 'NIST delta mm', 'Baseline delta mm']
    rows = []
    row_bg = []
    for i, (row) in enumerate(zip(chev_results['Energy MeV'],chev_results['D80 mm'],chev_results['Diff TPS mm'],chev_results['Diff NIST mm'],chev_results['Diff Baseline mm'])):
        rows.append(list(row))
        #format failed rows
        try:
            diff = abs(float(row[-1]))
        except:
            diff = 0.0
        if diff >= fail_threshold:
            row_bg.append([str(i), 'red'])
        elif diff >= warn_threshold:
            row_bg.append([str(i), 'orange'])
    tbl1 = sg.Table(values=rows, headings=row_titles,
                    auto_size_columns=True,
                    display_row_numbers=False,
                    justification='right', key='-TABLE-',
                    enable_events=True,
                    expand_x=True,
                    expand_y=True,
                    enable_click_events=False)
    layout2 = [[tbl1]]
    window2 = sg.Window("CHEVRON RESULTS", layout2, finalize=True)
    if row_bg:
        tbl1.update(row_colors=row_bg)
    _, _ = window2.read()
    if png_file:
        save_element_as_file(window2['-TABLE-'], png_file)
    window2.close()
    return

def read_db_data(fields):
    '''
        Helper function
        Return record from a table as a list
        If DB connection fails, return None
        Input dict fields:
            fields['target']        desired record field(s)
            fields['table']         table containing the records
            fields['filter_var']    field to filter records
            fields['filter_val']    value of filter field
        
        Return:
            data                    list of records
    '''

    target = fields['target']
    table = fields['table']
    filter_var = fields['filter_var']
    if filter_var:
        filter_val = fields['filter_val']

    conn=None

    if not DB_PATH:
        sg.popup("Path Error.","Provide a path to the Access Database.")
        print("Database Path Missing!")
        return None
    if PASSWORD:
        new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;PWD=%s'%(DB_PATH,PASSWORD) 
    else:
        new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s'%(DB_PATH)   
    try:  
        conn = pypyodbc.connect(new_connection)               
    except:
        print("Connection to table '"+table+"' failed...")
        sg.popup("Could not connect to database","WARNING")
        return None
    if isinstance(conn,pypyodbc.Connection):
        if filter_var:
            sql = '''
                    SELECT %s FROM %s WHERE %s = '%s'
                '''%(target, table, filter_var, filter_val)
        else:
            sql = '''
                    SELECT %s FROM %s
                '''%(target, table)
        cursor = conn.cursor()
        cursor.execute(sql)
        records = cursor.fetchall()
        cursor.close()
        conn.commit()
        conn = None
        data = []
        for row in records:
            if len(row)==1:
                data.append(row[0])
            else:
                data.append(list(row))
        return data
    else:
        return None

def write_session_data(conn,df_session,session_table,cols):
    '''
        Helper function
        Write to session table and return True if successful, else false
        Input:
            conn            database connection object
            df_session      dataframe of session table values
    ''' 
    cursor = conn.cursor() 
    vals = re.sub(r"([^,]+)", "?", cols) 
    sql = '''
            INSERT INTO "%s" (%s)
            VALUES (%s)
            '''%(session_table, cols, vals)
    data = df_session.values.tolist()[0] 
    print(data)
    print(cols)
    try:
        print("Writing session to database...")
        cursor.execute(sql, data)
        conn.commit()
        cursor.close()
        return True
    except IntegrityError:
        sg.popup("Session Write Error","WARNING: Write to database failed.")
        print("Integrity Error, nothing written to database")
        cursor.close()
        return False  


def write_results_data(conn,df_results,results_table,cols):
    '''
        Helper function
        Write results to table and return True if successful
        Input:
            conn            database connection object
            df_results      dataframe of results table values
            cols            string of comma separated database column names
        
        Return:
            write_flag      True if write successful, else False
    '''

    cursor = conn.cursor() 
    vals = re.sub(r"([^,]+)", "?", cols) 
    sql = '''
            INSERT INTO "%s" (%s)
            VALUES (%s)
            '''%(results_table, cols, vals)
    print("Writing results to database...")
    write_flag = True
    for row in df_results.values.tolist():
        try:
            cursor.execute(sql, row)
        except IntegrityError:
            sg.popup("Results Write Error","WARNING: Write to database failed.")
            print("Integrity Error, record not written to database:"+str(row))
            write_flag = False        
    conn.commit()
    cursor.close()
    return write_flag


def write_to_db(df_session,df_results,session_table,results_table,sess_cols,res_cols):
    '''
        Write session and results dataframes to tables
        Input:
            df_session      dataframe of session table values   
            df_results      dataframe of results table values
            sess_cols       string of comma separated database session column names
            res_cols        string of comma separated database results column names
    '''
    
    conn=None

    if not DB_PATH:
        sg.popup("Write Failed.","Provide a path to the Access Database.")
        return

    if PASSWORD:
        new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;PWD=%s'%(DB_PATH,PASSWORD) 
    else:
        new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s'%(DB_PATH)   

    try:  
        print('trying to connect')
        conn = pypyodbc.connect(new_connection)                 
    except:
        #sg.popup("Could not connect to database, nothing written","WARNING")
        print("Could not connect to database; nothing written")
    
    if isinstance(conn,pypyodbc.Connection):
        session_written = write_session_data(conn,df_session,session_table,sess_cols)
        print("Session "+session_table+" Write Status: "+str(session_written))
        if session_written:
            results_written = write_results_data(conn,df_results,results_table,res_cols)
            print("Results "+results_table+" Write Status: "+str(results_written))



def push_spot_session(session_data, conn, cursor):
    sql = '''
          INSERT INTO SpotPositionSession VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          '''
    try:
        cursor.execute(sql, session_data)
        conn.commit()
        return True
    except:
        conn = None
        return False


def push_spot_results(spot_results, conn, cursor):
    sql = '''
          INSERT INTO SpotPositionResults VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          '''
    try:
        for i, val in enumerate(spot_results):
            cursor.execute(sql, val)
            conn.commit()
    except:
        conn = None


### write spot grid data to DB
def spots_to_db(all_data=None, spotpatterns=None, values=None, values2={'-COMMENT2-': " PostISM"}):
    #adate = values['ADate'].strftime("%Y/%m/%d %H:%M:%S")
    if len(values['-ML-'])<255:
        session_comment = values['-ML-']
    else:
        session_comment = values['-ML-'][:255] 
    device = 'XRV-' + spotpatterns['240'].output.device
    gantry = values['-G-']
    # SpotPositionSession (8 entries)
    sess_data = [values['ADate'], gantry, device, values['GA'], values['-Op1-'], values['-Op2-'], session_comment, None]
    # push the session data to database
    new_connection = 'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;PWD=%s'%(DB_PATH,PASSWORD) 
    conn = pypyodbc.connect(new_connection) 
    cursor = conn.cursor()
    print("Writing session to database...")
    try:
        push_session = push_spot_session(sess_data, conn, cursor)
        print('Session SpotPositionSession Write Status: True')
    except:
        print('Session SpotPositionSession Write Status: False')
    if push_session == True:
        # push results data to database
        print("Writing results to database...")
        try:
            for key in all_data.keys():
                for i,_ in enumerate(all_data[key]):
                    all_data[key][i][0]=values['ADate']
                    all_data[key][i][1]=gantry
                push_spot_results(all_data[key], conn, cursor)
            print('Session SpotPositionResults Write Status: True')
            conn=None
        except:
            print('Session SpotPositionResults Write Status: False')
            conn=None

