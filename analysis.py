import re
import os
import glob
import subprocess
from chevron import *
from database_df import review_dose
import pandas as pd
import PySimpleGUI as sg
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, TableStyle, Table
from reportlab.lib.styles import ParagraphStyle
from PyPDF2 import PdfWriter , PdfReader 
import  spotanalysis
from spotanalysis.run_me import spot_data
import spotanalysis.spot_position_mod as spm
import spotanalysis.spot_position_func as spf
import spotanalysis.constants as cs
import spotanalysis.figures as fg
import spotanalysis.report as rp




#specify input params
db_cols = cs.db_cols
#data_dir = "O:\protons\Work in Progress\AlexG\PostISM_Jig\\test_data"
#current_path = os.path.abspath('.')
#current_path = os.path.abspath(os.path.dirname(__file__))
#gr_path = os.path.join(current_path, 'spotanalysis', 'def_gradient_ratio.png')
#prof_path  = os.path.join(current_path, 'spotanalysis', 'profiles_per_spot.png')
#gantry = 'Gantry 2'
#gantry_angle = '0'
#values = {'-G-': gantry, 'GA': gantry_angle,'ADate': '1900-01-01', '-Fldr-': data_dir, '-ML-': "TEST COMMENTS", '-Op1-': 'AGr', '-Op2-': ""}
#spotE = [240, 200, 150, 100, 70]



# sort folders and prepare report directory
def organise_logos_dirs(values=None):
    data_dir = values['-Logos-']
    data_date = re.sub('\D', '', values['ADate'][:10])
    report_dir = os.path.join(data_dir,'results_'+data_date)
    if os.path.isdir(report_dir):
        for f in os.listdir(report_dir):
            if re.match('.*\.png|.*\.pdf|.*\.xlsx|.*\.xls', f):
                print(f)
                os.remove(os.path.join(report_dir,f))
    os.makedirs(report_dir,exist_ok=True)
    fldrs = os.listdir(data_dir)
    chevron_dir = None
    spot_dirs = []
    for d in sorted(fldrs):
        fldr = os.path.join(data_dir,d)
        bmps = glob.glob(os.path.join(fldr,'*.bmp'))
        if len(bmps)==5:
            chevron_dir = fldr
        elif len(bmps)==1:
            spot_dirs.append(fldr)
    return chevron_dir, spot_dirs, report_dir

# create chevron results
def chevron_results(chevron_dir=None, values=None):
    chevron_analysis = chevron(chevron_dir).analyse(values['-G-'])
    chev_results = {}
    chev_results['Energy MeV'] = chevron_analysis['MeV'][0]
    chev_results['D80 mm'] = [round(x,2) for x in chevron_analysis['BPD']]
    chev_results['Diff TPS mm'] = [round(x,2) for x in chevron_analysis['Diff_TPS']]
    chev_results['Diff NIST mm'] = [round(x,2) for x in chevron_analysis['Diff_NIST']]
    chev_results['Diff Baseline mm'] = [round(x,2) for x in chevron_analysis['Diff_Baseline']]
    return chev_results

# create output results
def output_results(results=None):
    op_results = {}
    duplicate_flag = [True]
    for i,e in enumerate(results['Energy'][1:]):
        if results['Energy'][i]==e:
            duplicate_flag.append(False)
        else:
            duplicate_flag.append(True)

    op_results['Energy MeV'] = [int(i) for i,f in zip(results['Energy'],duplicate_flag) if f]
    op_results['D mean Gy'] = [round(float(x),4) for x,f in zip(results['RavgGy'],duplicate_flag) if f]
    op_results['D ref Gy'] = [round(float(x),4) for x,f in zip(results['Rref'],duplicate_flag) if f]
    op_results['R range'] = [round(float(x),3) for x,f in zip(results['Rrange prcnt'],duplicate_flag) if f]
    op_results['D diff'] = [round(float(x),3) for x,f in zip(results['Rdelta'],duplicate_flag) if f]
    print(op_results)
    return op_results

# create spot grid results
def spot_results(spot_dirs=None, spotE=None, values=None, db_cols=cs.db_cols):
    spotpatterns = {}
    # for i in range(1, nbmp+1):
    print("Processing spots...")
    for E, bmp_loc in zip(spotE,spot_dirs):
        str1 = str(E)
        str2 = glob.glob(os.path.join(bmp_loc,'*.bmp'))
        spotpatterns.update({str1: spm.SpotPattern(str2[0])})

    gui_values ={'-GANTRY-': values['-G-'], '-GANTRY_ANGLE-': values['GA']}
    print('Making Spot Data dataset...')
    all_data, device= spot_data(gui_values, spotpatterns)
    # ## start analysis
    df = []
    for key in all_data.keys():
        df.extend(all_data[key][:])

    df = pd.DataFrame(df, columns = db_cols)
    df = spf.calc_shifts(df, device)
    return df, device, spotpatterns, all_data

# write spot grid report
def spot_report(df=None, device=None, report_dir=None, values=None, energies=[240, 200, 150, 100, 70]):
    # change active dir
    current_path = os.path.abspath(os.path.dirname(__file__))
    gr_path = os.path.join(current_path,'spotanalysis','def_gradient_ratio.png')
    prof_path = os.path.join(current_path,'spotanalysis','profiles_per_spot.png')
    os.chdir(report_dir)

    # results to excel
    df.to_excel(os.path.join(report_dir,'result.xlsx'))

    # absolute plot
    fg.plot_spot_grid(df, device, tolerance = 2)
    fg.plot_shifts(df, device, tolerance = 2)
    fg.plot_shifts_by_energy(df, device, tolerance =2 )
    fg.plot_shifts_by_pos(df, device, tolerance = 2 )

    # relative plot
    fg.plot_spot_grid(df, device, tolerance=1)
    fg.plot_shifts(df, device, tolerance=1)
    fg.plot_shifts_by_energy(df, device, tolerance =1 )
    fg.plot_shifts_by_pos(df, device, tolerance = 1 )
    fg.plot_distribution(df)
    fg.plot_fwhm(df)

    # results tables and report generation
    rp.make_table(df, energies)
    rp.spot_report(df, values['-Op1-'], values['-Op2-'], report_dir, gr_path, prof_path, values['-ML-'], energies)
    os.chdir(current_path)
    return


# report helper functions
def _dict_to_table(dict=None):
    keys = list(dict.keys())
    l=len(dict[keys[0]])
    tbl = []
    tbl.append(keys)
    for r in range(l):
        row = [dict[x][r] for x in dict.keys()]
        tbl.append(row)
    table = Table(np.array(tbl).tolist())
    table.setStyle(TableStyle([('VALIGN', (0,0), (-1, -1), 'MIDDLE'), ('ALIGN', (0,0), (-1, -1), 'CENTER'), \
                            ('BACKGROUND', (0, 0), (-1, -1), colors.lemonchiffon), ('BOX', (0, 0), (-1, -1), 2, colors.black), \
                            ('BOX', (0, 0), (-1, 0), 2, colors.black)]))
    return table


def _highlight_fails(table=None, column_index=0, fail_threshold=None, warn_threshold=None):
    for i, row in enumerate(table._cellvalues):
        try:
            val = abs(float(row[column_index]))
        except:
            val = 0
        if val>=fail_threshold:
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.lightcoral)]))
        elif val>warn_threshold:
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.lightsalmon)]))
    return table

# write chevron report
def chev_report(chev_results=None, values=None, fail_oot=1.0, warn_oot=0.5, pdf_name='chevron_report.pdf', gantry_angle=0):
    print('staring chevron report')
    doc = SimpleDocTemplate(pdf_name,pagesize=letter,
                        rightMargin=72,leftMargin=72,
                        topMargin=72,bottomMargin=18)

    hp = ParagraphStyle('Normal')
    hp.textcolor = 'black'
    hp.fontsize = 10
    hp.fontName = 'Helvetica-Bold'
    hp.spaceAfter = 6
    hp.leading = 16
    hp.underlineWidth = 1

    bp = ParagraphStyle('Normal')
    bp.textcolor = 'black'
    bp.fontsize = 10
    bp.fontName = 'Helvetica'
    bp.spaceBefore = 3
    bp.spaceAfter = 3
    hp.leading = 12

    sp = ParagraphStyle('Normal')
    sp.textcolor = 'black'
    sp.fontsize = 15
    sp.fontName = 'Helvetica-Bold'
    sp.spaceBefore = 6
    sp.spaceAfter = 6
    sp.leading = 12

    story = []

    #  chevron report header
    report_title = '%s Chevron Energy Range Analysis' % values['-G-']
    story.append(Paragraph(report_title, hp))
    story.append(Paragraph("Date: "+values['ADate'], bp))
    story.append(Paragraph("Gantry: "+values['-G-'], bp))
    story.append(Paragraph("Gantry Angle: "+str(gantry_angle)+" degrees", bp))
    story.append(Paragraph("Operator(s): "+values['-Op1-']+" "+values['-Op2-'], bp))
    story.append(Spacer(1, 5))
    # Chevron results
    story.append(Paragraph('Result summary:', sp))
    story.append(Spacer(1, 5))
    t = _dict_to_table(chev_results)
    # highlight OOT
    t = _highlight_fails(table=t, column_index=-1, fail_threshold=fail_oot, warn_threshold=warn_oot)
    story.append(t)
    story.append(Spacer(1, 20))
    # build report
    doc.build(story)
    print('Chevron report complete')
    return

# write output report
def output_report(results=None, values=None, fail_oot=1.0, warn_oot=0.5, pdf_name='output_report.pdf', gantry_angle=0):
    print('Starting output report')
    doc = SimpleDocTemplate(pdf_name,pagesize=letter,
                        rightMargin=72,leftMargin=72,
                        topMargin=72,bottomMargin=18)

    hp = ParagraphStyle('Normal')
    hp.textcolor = 'black'
    hp.fontsize = 10
    hp.fontName = 'Helvetica-Bold'
    hp.spaceAfter = 6
    hp.leading = 16
    hp.underlineWidth = 1

    bp = ParagraphStyle('Normal')
    bp.textcolor = 'black'
    bp.fontsize = 10
    bp.fontName = 'Helvetica'
    bp.spaceBefore = 3
    bp.spaceAfter = 3
    hp.leading = 12

    sp = ParagraphStyle('Normal')
    sp.textcolor = 'black'
    sp.fontsize = 15
    sp.fontName = 'Helvetica-Bold'
    sp.spaceBefore = 6
    sp.spaceAfter = 6
    sp.leading = 12

    story = []

    #  output consistency report header
    report_title = '%s Output Consistency Analysis' % values['-G-']
    story.append(Paragraph(report_title, hp))
    story.append(Paragraph("Date: "+values['ADate'], bp))
    story.append(Paragraph("Gantry: "+values['-G-'], bp))
    story.append(Paragraph("Gantry Angle: "+str(gantry_angle)+" degrees", bp))
    story.append(Paragraph("Operator(s): "+values['-Op1-']+" "+values['-Op2-'], bp))
    story.append(Spacer(1, 5))
    # output consistency results
    story.append(Paragraph('Result summary:', sp))
    story.append(Spacer(1, 5))
    t = _dict_to_table(results)
    # highlight OOT
    t = _highlight_fails(table=t, column_index=-1, fail_threshold=fail_oot, warn_threshold=warn_oot)
    story.append(t)
    story.append(Spacer(1, 20))
    # build report
    doc.build(story)
    print('output report complete')
    return


# merge all three reports
def merge_reports(reports=[], report_name='PostISM_Report.pdf'):
    # initialise pdf writer
    output = PdfWriter()
    # read existing PDF reports to writer
    for report_pdf in reports:
        existingPdf = PdfReader(open(report_pdf, 'rb'))
        output.append_pages_from_reader(existingPdf)
    # write merged report to file
    outputStream = open(report_name, 'wb')
    output.write(outputStream)
    outputStream.close()
    return


