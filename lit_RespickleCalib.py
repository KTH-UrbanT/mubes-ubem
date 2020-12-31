import pickle
import matplotlib.pyplot as plt
from matplotlib import gridspec
import os, sys
#add the required path



signature =False
path = 'C:\\Users\\xav77\\Documents\\FAURE\\prgm_python\\UrbanT\\Eplus4Mubes\\MUBES_UBEM\\CaseFiles\\Sim_Results\\'

os.chdir(path)
liste = os.listdir()
zone1 = {}
for i in liste:
    if '.pickle' in i:
        with open(i, 'rb') as handle:
            zone1[int(i[i.index('v')+1:i.index('.')])] = pickle.load(handle)



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
heat1 = []
cool1 = []
tot1 = []
nbbuild = []
EPC_elec = []
EPC_Heat = []
EPC_Cool = []
EPC_Tot = []
TotelPower = {}
EPareas1 =[]
DBareas = []
EnergieTot = []
EnvLeak = []
for i,key in enumerate(zone1):
    elec1.append(zone1[key]['EnergyConsVal'][1]/3.6/zone1[key]['EPlusHeatArea']*1000) #convert GJ in kWh/m2
    cool1.append(zone1[key]['EnergyConsVal'][4]/3.6/zone1[key]['EPlusHeatArea']*1000)
    heat1.append(zone1[key]['EnergyConsVal'][5]/3.6/zone1[key]['EPlusHeatArea']*1000)
    tot1.append((zone1[key]['EnergyConsVal'][1]+zone1[key]['EnergyConsVal'][4]+zone1[key]['EnergyConsVal'][5])/3.6/zone1[key]['EPlusHeatArea']*1000) #to have GJ into kWh/m2
    eleval = 0
    for x in zone1[key]['EPCMeters']['ElecLoad']:
        if zone1[key]['EPCMeters']['ElecLoad'][x]:
            eleval += zone1[key]['EPCMeters']['ElecLoad'][x]
    EPC_elec.append(eleval/zone1[key]['EPlusHeatArea'])
    heatval = 0
    for x in zone1[key]['EPCMeters']['Heating']:
        heatval += zone1[key]['EPCMeters']['Heating'][x]
    EPC_Heat.append(heatval/zone1[key]['EPlusHeatArea'])
    coolval = 0
    for x in zone1[key]['EPCMeters']['Cooling']:
        coolval += zone1[key]['EPCMeters']['Cooling'][x]
    EPC_Cool.append(coolval/zone1[key]['EPlusHeatArea'])
    EPC_Tot.append((eleval+heatval+coolval)/zone1[key]['EPlusHeatArea'])
    EPareas1.append(zone1[key]['EPlusHeatArea'])
    DBareas.append(zone1[key]['DataBaseArea'])
    TotelPower[key] = [zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Cooling Rate'][i] +
                      zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate'][i] +
                      zone1[key]['HeatedArea']['Data_Electric Equipment Total Heating Rate'][i]
                      for i in range(len(zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate']))]
    EnergieTot.append(sum(TotelPower[key])/1000/zone1[key]['EPlusHeatArea'])
    nbbuild.append(key)
    EnvLeak.append(zone1[key]['EnvLeak'])

fig =plt.figure(0)
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,elec1,'s')
ax0.plot(nbbuild, EPC_elec,'x')
ax0.grid()
plt.title('Elec_Load (kWh\m2)')
ax1 = plt.subplot(gs[-1,0])
ax1.plot(nbbuild, [(elec1[i]-EPC_elec[i])/EPC_elec[i]*100 for i in range(len(heat1))],'x')
ax1.grid()
#ax1.title('mono-multi')
plt.tight_layout()

fig1 =plt.figure()
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,heat1,'s')
ax0.plot(nbbuild, EPC_Heat,'x')
ax0.grid()
plt.title('Heat (kWh\m2)')
ax1 = plt.subplot(gs[-1,0])
ax1.plot(nbbuild, [(heat1[i]-EPC_Heat[i])/EPC_Heat[i]*100 for i in range(len(heat1))],'s')
ax1.grid()
#ax1.title('mono-multi')
plt.tight_layout()


fig2 =plt.figure()
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,cool1,'s')
ax0.plot(nbbuild, EPC_Cool,'x')
ax0.grid()
plt.title('Cool (kWh\m2)')
ax1 = plt.subplot(gs[-1,0])
#ax1.plot(nbbuild, [(cool1[i]-EPC_Cool[i])/cool1[i]*100 for i in range(len(cool1))],'s')
ax1.grid()
#ax1.title('mono-multi')
plt.tight_layout()


fig3 =plt.figure()
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:,0])
ax0.plot(EnvLeak, [(EPC_Tot[i]-tot1[i])/EPC_Tot[i]*100 for i in range(len(cool1))],'x')
ax0.grid()
plt.xlabel('EnvLeak (l/s/m2 at 50Pa)')
plt.ylabel('(Meas - Sim)/Mes (%)')

#ax1.title('mono-multi')
plt.tight_layout()

fig4 = plt.figure()
gs = gridspec.GridSpec(4, 1)
ax0 = plt.subplot(gs[:-1,0])
ax0.plot(nbbuild,tot1,'s')
ax0.plot(nbbuild,EPC_Tot,'x')
#ax0.plot(nbbuild,EnergieTot,'>')
ax0.grid()
plt.title('Tot (kWh/m2)')
ax1 = plt.subplot(gs[-1,0])
ax1.plot(nbbuild, [(EPC_Tot[i]-tot1[i])/EPC_Tot[i]*100 for i in range(len(cool1))],'x')
ax1.grid()
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
        ax0.plot(zone1[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Heating Rate'],'.')
        ax0.plot(zone1[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 zone1[key]['HeatedArea']['Data_Zone Ideal Loads Supply Air Total Cooling Rate'],'.')
        ax0.plot(zone1[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 zone1[key]['HeatedArea']['Data_Zone Ideal Loads Heat Recovery Total Heating Rate'],'.')
        ax0.plot(zone1[key]['OutdoorSite']['Data_Site Outdoor Air Drybulb Temperature'],
                 zone1[key]['HeatedArea']['Data_Zone Ideal Loads Heat Recovery Total Cooling Rate'],'.')
        plt.title('Building_'+str(key))

plt.show()