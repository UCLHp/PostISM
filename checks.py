import PySimpleGUI as sg
import os
import datetime
import re

def pre_analysis_check(values, layers):
    '''
        Check GUI values are valid
        Input:
            values                  GUI values dict

        Returns list of lists check_fail:
            check_fail[n][0]       True if check n failed
            check_fail[n][1]       unique int for check n
    '''
    check_fail = [[False,0]]     
    
    # helper functions
    def _range_check(value, key, minval, maxval):
        if not maxval >= value >= minval:
            sg.popup("Invalid Value", "Enter a valid "+key+" between "+str(minval)+" and "+str(maxval))
            return True
        else:
            return False
    
    # check ADate
    try:
        adate = datetime.datetime.strptime(values['ADate'],"%Y/%m/%d %H:%M:%S")
    except:
        sg.popup("Invalid Value", "Select a valid Date (yyyy/mm/dd hh:mm:ss)")
        check_fail.append([True,1])
        return check_fail

    # check temperature
    try:
        check_flag = _range_check(float(values['Temp']), 'Temperature', 18., 26.)
        if check_flag:
            check_fail.append([check_flag,2])
            return check_fail
    except:
        sg.popup("Invalid Value","Temperature error, check entered value")
        check_fail.append([True,3])
        return check_fail

    # check pressure
    try:
        check_flag = _range_check(float(values['Press']), 'Pressure', 955, 1055)
        if check_flag:
            check_fail.append([check_flag,4])
            return check_fail
    except:
        sg.popup("Invalid Value","Pressure error, check entered value")
        check_fail.append([True,5])
        return check_fail

    # check gantry angle
    try:
        if not 0 <= int(values['GA']) <= 359:
            sg.popup("Invalid Value","Enter an integer gantry angle between 0 and 359")
            check_fail.append([True,6])
            return check_fail
    except:
        sg.popup("Invalid Value","Gantry angle error, check entered value")
        check_fail.append([True,7])
        return check_fail
    
    # check readings are deimcal or blank
    r = []
    try:
        for n,_ in enumerate(layers[0]):
            i = str(n)
            lst = [values['r'+i+'1'],values['r'+i+'2']]
            r.extend([x for x in lst if not re.fullmatch(r'^(?:[0-9]+(?:\.[0-9]*)?)?$', x)])
        if len(r)!=0:
           sg.popup("Invalid Value","Ensure all readings are positive decimal numbers")
           check_fail.append([True,8])
           return check_fail
    except:
        sg.popup("Invalid Value","R error, check entered values: " +str(layers))
        check_fail.append([True,9])
        return check_fail
    
    # check operator
    if values['-Op1-'] == '':
        check_fail.append([True,10])
        sg.popup("Invalid Value", "Select Operator 1 initials")
        return check_fail
    
    # check gantry, chamber, electrometer, voltage
    equipment = {'Gantry':'-G-','Chamber':'-Ch-','Electrometer':'-El-','Voltage':'-V-'}
    for n in equipment:
        if values[equipment[n]] == '':
            check_fail.append([True,11])
            sg.popup("Invalid Value", "Select a value for: "+n)
            return check_fail

    # check Humidity
    try:
        if not 0 <= float(values['H']) <= 100:
            sg.popup("Invalid Value","Enter a percentage humidity between 0 and 100")
            check_fail.append([True,12])
            return check_fail
    except:
        sg.popup("Invalid Value","Humidity error, check entered value")
        check_fail.append([True,13])
        return check_fail
    
    # check chevron directory
    if not os.path.exists(values['-Logos-']):
        sg.popup("Invalid Logos Data","Specified Logos directory does not exist")
        check_fail.append([True,14])
        return check_fail
    
    return check_fail