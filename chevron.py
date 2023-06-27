import glob
import os
import json
import csv
import re
import numpy as np
import cv2
import pandas as pd
from types import SimpleNamespace   

class chevron():
    def __init__(self, data_dir):
        # specify Logos file paths
        self.dir = data_dir
        bmp_list = glob.glob(os.path.join(data_dir,"*.bmp"))
        #output file
        output_name = os.path.join(data_dir,"output.txt")
        #activescript file
        activescript = os.path.join(data_dir,"activescript.txt")

        self.bmp_list = bmp_list
        self.output_name = output_name
        self.activescript = activescript
        self.MachineNames = ['Gantry 1', 'Gantry 2', 'Gantry 3', 'Gantry 4']


    def analyse(self, gantry=None):
        # load Logos calibration params
        cal_dict = self._load_calibration()
        cal = SimpleNamespace(**cal_dict)
                
        #calculate chevron-specific params
        scaling = []
        for i in cal.h:
            scaling.append( (cal.SAD_Y - (i-cal.LCW_half_width)) / cal.SAD_Y )

        # initialise results dict
        r = {
            'X': [],
            'Y': [],
            'fps': [],
            'dB': [],
            'MeV': [],
            'fldr': [],
            'BPD': [],
            'A': [],
            'B': [],
            'C': [],
            'D': [],
            'E': [],
            'F': [],
            'Acntr': [],
            'Bcntr': [],
            'Ccntr': [],
            'Dcntr': [],
            'Ecntr': [],
            'Fcntr': [],
            'HRatio': [],
            'VRatio': [],
            'NIST': [],
            'TPS': [],
            }

        # read activescript
        HRatio, VRatio = self._load_activescript()

        # read output.txt and write to results dict
        with open(self.output_name, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            c=1000
            for i,row in enumerate(reader):
                if i==0:
                    X = float(row[5].strip())
                    Y = float(row[6].strip())
                    fps = float(row[8].strip())
                    dB = float(row[12].strip())
                
                if 'Image:' in row:
                    image = int(row[1].strip())
                    c = i
                
                if 0 < i-c <= 1:
                    r['A'].append(float(row[4].strip()))
                    r['Acntr'].append(float(row[3].strip()))
                
                if 1 < i-c <= 2:
                    r['B'].append(float(row[4].strip()))
                    r['Bcntr'].append(float(row[3].strip()))
                
                if 2 < i-c <= 3:
                    r['C'].append(float(row[4].strip()))
                    r['Ccntr'].append(float(row[3].strip()))
                
                if 3 < i-c <= 4:
                    r['D'].append(float(row[4].strip()))
                    r['Dcntr'].append(float(row[3].strip()))
                
                if 4 < i-c <= 5:
                    r['E'].append(float(row[4].strip()))
                    r['Ecntr'].append(float(row[3].strip()))
                
                if 5 < i-c <= 6:
                    r['F'].append(float(row[4].strip()))
                    r['Fcntr'].append(float(row[3].strip()))

        # write remaining vars to results dict
        r['X'] = [X]*len(r['A'])
        r['Y'] = [Y]*len(r['A'])
        r['fps'] = [fps]*len(r['A'])
        r['dB'] = [dB]*len(r['A'])
        r['HeightA'] = [cal.h[0]]*len(r['A'])
        r['HeightB'] = [cal.h[1]]*len(r['B'])
        r['HeightC'] = [cal.h[2]]*len(r['C'])
        r['HeightD'] = [cal.h[3]]*len(r['D'])
        r['HeightE'] = [cal.h[4]]*len(r['E'])
        r['HeightF'] = [cal.h[5]]*len(r['F'])
        r['MeV'] = [cal.MeV]*len(r['A'])
        r['fldr'] = [self.json_dir]*len(r['A'])
        r['HRatio'] = [HRatio]*len(r['A'])
        r['VRatio'] = [VRatio]*len(r['A'])
        r['NIST'] = cal.D80_NIST
        r['TPS'] = cal.D80_TPS

        # calculate range
        for i in range(len(r['A'])):
            BPD = []
            for j, c in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
                #optical scaling
                s = scaling[j]
                #BPD
                bpd = cal.Target_l*cal.Target_WER+cal.Chevron_WER*(cal.h[j]-(r[c][i]*s)/2)
                #SAD correction
                sady = r[c][i]*r[c][i] / (4*cal.SAD_Y*cal.SAD_Y) + 1
                sadx = r[c+'cntr'][i]*r[c+'cntr'][i] / (cal.SAD_X*cal.SAD_X) + 1
                sad = np.sqrt(sady+sadx-1)
                bpd_corr = bpd*sad
                if r[c][i] != 0:
                    BPD.append(bpd_corr)
            r['BPD'].append(np.mean(BPD))        
        
        # calculate difference from references
        if gantry in self.MachineNames:
            r['Baseline'] = cal.D80_Baseline[gantry]
            r['Diff_Baseline'] = list(np.array(r['BPD']) - np.array(r['Baseline']))
        r['Diff_NIST'] = list(np.array(r['BPD']) - np.array(r['NIST']))
        r['Diff_TPS'] = list(np.array(r['BPD']) - np.array(r['TPS']))
        return r
    

    def _load_calibration(self,json_name=None):
        # load Logos config file
        if json_name is None:
            json_name = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logos_config.json')) 
        with open(json_name, 'r') as j:
            jsonDict = json.load(j)
        
        self.json_dir = json_name
        return jsonDict
    

    def _load_bmp(self):        
        # load images to list of 2D numpy arrays
        img = [cv2.imread(i, cv2.IMREAD_GRAYSCALE).astype(float) for i in self.bmp_list]
        return img


    def _load_activescript(self):
        CameraHRatio=None
        CameraVRatio=None
        flag=0
        # read activescript.txt file
        f = open(self.activescript)
        for line in f:
            if "CameraHRatio" in line:
                CameraHRatio = float(re.findall("\d+\.\d+", line)[0])
                flag += 1
            elif "CameraVRatio" in line:
                CameraVRatio = float(re.findall("\d+\.\d+", line)[0])
                flag += 1
            elif flag==2:
                break        
        return CameraHRatio, CameraVRatio
    

    def analyse_to_df(self, gantry=None):
        r = self.analyse(gantry)
        df = pd.DataFrame.from_dict(r)
        df.to_excel('here.xlsx')


### helper function
def load_calibration(json_name=None):
    # load Logos config file
    if json_name is None:
        json_name = os.path.abspath(os.path.join(os.path.dirname(__file__), 'logos_config.json')) 
    with open(json_name, 'r') as j:
        jsonDict = json.load(j)    
    return jsonDict




