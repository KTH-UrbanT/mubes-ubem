import pickle
import matplotlib.pyplot as plt
from matplotlib import gridspec
import os, sys
#add the required path
path2addgeom = os.path.dirname(os.getcwd()) + '\\geomeppy'
#path2addeppy = os.path.dirname(os.getcwd()) + '\\eppy'
#sys.path.append(path2addeppy)
sys.path.append(path2addgeom)
from geomeppy import IDF


signature =False
path = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFiles10\\Sim_Results\\'
path1zone = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFiles10\\Sim_Results\\'

os.chdir(path1zone)
liste = os.listdir()
zone1 = {}
SimNumb = []
for i in liste:
    if '.pickle' in i:
        with open(i, 'rb') as handle:
            try:
                num = int(i[i.index('v') + 1:i.index('.')])
            except:
                num = int(i[i.index('_') + 1:i.index('.')])
            SimNumb.append(num)
            zone1[SimNumb[-1]] = pickle.load(handle)


os.chdir(path)
liste = os.listdir()
zone2 = {}
SimNumb = []
for i in liste:
    if '.pickle' in i:
        with open(i, 'rb') as handle:
            try:
                num = int(i[i.index('v') + 1:i.index('.')])
            except:
                num = int(i[i.index('_') + 1:i.index('.')])
            SimNumb.append(num)
            zone2[SimNumb[-1]] = pickle.load(handle)



for i,key in enumerate(zone1.keys()):
    if i==0:
        print('First key :' + str(zone1[key].keys()))
        for key1 in zone1[key].keys():
            if isinstance(zone1[key][key1],dict):
                keytoprnit = [key for key in zone1[key][key1].keys() if 'Data' in key]
                for nb in keytoprnit:
                    print(nb)
                break



elec1 = []
elec2 = []
heat1 = []
heat2 = []
cool1 = []
cool2 = []
tot1 = []
tot2 = []
nbbuild = []
EPC_elec = []
EPC_Heat = []
EPC_Cool = []
EPC_Tot = []
TotelPower = {}
EPareas1 =[]
EPareas2 =[]
DBareas = []
EnergieTot = []
for i,key in enumerate(zone1):
    Ref_Area = zone1[key]['EPlusHeatArea'] #zone1[key]['DataBaseArea']  #
    elec1.append(zone1[key]['EnergyConsVal'][1]/3.6/zone1[key]['EPlusHeatArea']*1000) #convert GJ in kWh/m2
    elec2.append(zone2[key]['EnergyConsVal'][1]/3.6/zone2[key]['EPlusHeatArea']*1000)
    cool1.append(zone1[key]['EnergyConsVal'][4]/3.6/zone1[key]['EPlusHeatArea']*1000)
    cool2.append(zone2[key]['EnergyConsVal'][4]/3.6/zone2[key]['EPlusHeatArea']*1000)
    heat1.append(zone1[key]['EnergyConsVal'][5]/3.6/zone1[key]['EPlusHeatArea']*1000)
    heat2.append(zone2[key]['EnergyConsVal'][5]/3.6/zone2[key]['EPlusHeatArea']*1000)
    tot1.append((zone1[key]['EnergyConsVal'][1]+zone1[key]['EnergyConsVal'][4]+zone1[key]['EnergyConsVal'][5])/3.6/zone1[key]['EPlusHeatArea']*1000) #to have GJ into kWh/m2
    tot2.append((zone2[key]['EnergyConsVal'][1]+zone2[key]['EnergyConsVal'][4]+zone2[key]['EnergyConsVal'][5])/3.6/zone2[key]['EPlusHeatArea']*1000)
    eleval = 0
    val = zone1[key]['BuildDB']
    for x in val.EPCMeters['ElecLoad']:
        if val.EPCMeters['ElecLoad'][x]:
            eleval += val.EPCMeters['ElecLoad'][x]
    EPC_elec.append(eleval/Ref_Area)
    heatval = 0
    for x in val.EPCMeters['Heating']:
        heatval += val.EPCMeters['Heating'][x]
    EPC_Heat.append(heatval/Ref_Area)
    coolval = 0
    for x in val.EPCMeters['Cooling']:
        coolval += val.EPCMeters['Cooling'][x]
    EPC_Cool.append(coolval/zone2[key]['EPlusHeatArea'])
    EPC_Tot.append((eleval+heatval+coolval)/Ref_Area)
    EPareas1.append(zone1[key]['EPlusHeatArea'])
    EPareas2.append(zone2[key]['EPlusHeatArea'])
    DBareas.append(val.surface)
    # TotelPower[key] = [zone2[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Cooling Rate'][i] +
    #                   zone2[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate'][i] +
    #                   zone2[key]['HeatedArea']['Data_Electric Equipment Total Heating Rate'][i]
    #                   for i in range(len(zone2[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate']))]
    # EnergieTot.append(sum(TotelPower[key])/1000/zone2[key]['EPlusHeatArea'])
    nbbuild.append(key)

fig =plt.figure(0)
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,elec1,'s', label= 'Elec1')
#ax0.plot(nbbuild,elec2,'o', label = 'Elec2')
ax0.plot(nbbuild, EPC_elec,'x', label = 'EPC')
ax0.grid()
ax0.legend()
ax0.set_xlabel('Building nb')
ax0.set_ylabel('Elec_Load (kWh\m2)')
#plt.title('Elec_Load (kWh\m2)')
ax1 = plt.subplot(gs[-1,0])
ax1.plot(nbbuild, [(elec1[i]-EPC_elec[i])/EPC_elec[i]*100 for i in range(len(heat1))],'x', label = '(Elec1-EPC)\EPC (%)')
ax1.legend()
ax1.grid()
#ax1.title('mono-multi')
plt.tight_layout()

fig1 =plt.figure()
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,heat1,'s', label= 'Int Ins')
ax0.plot(nbbuild,heat2,'o', label= 'Ext Ins')
#ax0.plot(nbbuild, EPC_Heat,'x', label= 'EPC')
ax0.grid()
ax0.legend()
ax0.set_xlabel('Building nb')
ax0.set_ylabel('Heat needs (kWh\m2)')
#plt.title('Heat (kWh\m2)')
ax1 = plt.subplot(gs[-1,0])
ax1.plot(nbbuild, [(heat1[i]-heat2[i])/heat2[i]*100 for i in range(len(heat1))],'s', label = '(II-EI)\EI (%)')
ax1.grid()
ax1.legend()
#ax1.title('mono-multi')
plt.tight_layout()


fig2 =plt.figure()
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,cool1,'s', label= 'Cool1')
ax0.plot(nbbuild,cool2,'o', label= 'Cool2')
ax0.plot(nbbuild, EPC_Cool,'x', label= 'EPC')
ax0.grid()
ax0.legend()
plt.title('Cool (kWh\m2)')
ax1 = plt.subplot(gs[-1,0])
#ax1.plot(nbbuild, [(cool1[i]-EPC_Cool[i])/cool1[i]*100 for i in range(len(cool1))],'s')
ax1.grid()
ax1.legend()
#ax1.title('mono-multi')
plt.tight_layout()


fig3 =plt.figure()
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,EPareas1,'s', label= 'Area1')
ax0.plot(nbbuild,EPareas2,'o', label= 'Area2')
ax0.plot(nbbuild,DBareas,'x', label= 'DataBase ATemp')
ax0.grid()
ax0.legend()
plt.title('Areas (m2)')
ax1 = plt.subplot(gs[-1,0])
ax1.plot(nbbuild, [(EPareas1[i]-DBareas[i])/EPareas1[i]*100 for i in range(len(EPareas1))],'s', label= '(EPAera-Atemp)/EPArea (%)')
#ax1.plot(nbbuild, [(EPareas2[i]-DBareas[i])/EPareas2[i]*100 for i in range(len(EPareas1))],'x')
ax1.grid()
ax1.legend()
#ax1.title('mono-multi')
plt.tight_layout()

fig4 = plt.figure()
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,tot1,'s', label= 'Tot1')
ax0.plot(nbbuild,tot2,'o', label= 'Tot2')
ax0.plot(nbbuild,EPC_Tot,'x', label= 'EPC')
#ax0.plot(nbbuild,EnergieTot,'>')
ax0.grid()
ax0.legend()
plt.title('Tot (kWh/m2)')
ax1 = plt.subplot(gs[-1,0])
ax1.plot(nbbuild, [(tot1[i]-tot2[i])/tot2[i]*100 for i in range(len(cool1))],'x', label= '(Tot1-Tot2)/Tot2 (%)')
ax1.plot(nbbuild, [(EPC_Tot[i]-tot1[i])/EPC_Tot[i]*100 for i in range(len(cool1))],'x', label= '(EPC-Tot1)/EPC (%)')
ax1.grid()
ax1.legend()
#ax1.title('mono-multi')
plt.tight_layout()

if signature:
    fig = plt.figure()
    posy = -1
    gs = gridspec.GridSpec(int(len(zone1)**0.5)+1, round(len(zone1)**0.5))
    for i,key in enumerate(zone1):
        posx = i%(int(len(zone1)**0.5)+1) # if i<=int(len(zone1)/2) else int(len(zone1)/2)
        if posx==0:
            posy += 1# i%(round(len(zone1)/2)) #0 if posx<int(len(zone1)/2) else i-posx
        ax0 = plt.subplot(gs[posx, posy])
        ax0.plot(zone1[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],zone2[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate'],'.')
        ax0.plot(zone1[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Cooling Rate'],'.')
        ax0.plot(zone1[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 zone1[key]['HeatedArea']['Data_Zone Ideal Loads Heat Recovery Total Heating Rate'],'.')
        ax0.plot(zone1[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 zone1[key]['HeatedArea']['Data_Zone Ideal Loads Heat Recovery Total Cooling Rate'],'.')
        plt.title('Building_'+str(key))

plt.show()