# @Author  : Xavier Faure
# @Email   : xavierf@kth.se


def createNewConstruction(idf,Name,Material):
    idf.newidfobject(
        "CONSTRUCTION", Name=Name, Outside_Layer=Material
    )

def create_MaterialObject(idf, Name, Material):
    if 'Window' in Name:
        idf.newidfobject(
            'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
            Name=Name,
            UFactor=Material['UFactor'],
            Solar_Heat_Gain_Coefficient=Material['Solar_Heat_Gain_Coefficient'],
            Visible_Transmittance=Material['Visible_Transmittance'],
        )
        # this is for having shading on the indoor face of each window
        # idf.newidfobject(
        #     'WINDOWMATERIAL:SHADE',
        # Name = 'Interior_Shade',
        # Solar_Transmittance = 0.01,
        # Solar_Reflectance = 0.05,
        # Visible_Transmittance = 0.01,
        # Visible_Reflectance = 0.05,
        # Infrared_Hemispherical_Emissivity = 0.01,
        # Infrared_Transmittance = 0.05,
        # Thickness = 0.01,
        # Conductivity = 0.1,
        # )
    else:
        Material['Name'] = Name
        idf.newidfobject(
                'MATERIAL',
                **Material)
    return idf

def CreateAirwallsMat(idf):
        # idf.newidfobject(         #this was a try to take into account for transperant partition between core/perim nbut also between blocs.... is there any sence ??
        #     'MATERIAL:INFRAREDTRANSPARENT',
        #     Name = 'AirWallMaterial',
        # )
        idf.newidfobject(
            'MATERIAL',
            Name = 'AirWallMaterial',
            Thickness = 0.01,
            Conductivity = 0.6,
            Roughness = "MediumSmooth",
            Density = 800,
            Specific_Heat = 1000,
            Thermal_Absorptance = 0.95,
            Solar_Absorptance = 0.7,
            Visible_Absorptance = 0.7,
        )

def create_Material(idf, Material, MaterialUpgrade, Ret):
    # Window_U0value =  {'0': 2.7, '1939':2.7, '1960':2.7, '1970':2.5, '1976':2, '1985':1.8, '2000':1.2} #todo delete
    # Template_Wind = sorted([item for item in Window_U0value if float(item) <= year], reverse=True)[0]
    # uval_window = Window_U0value[Template_Wind]
    # newUval = 1/(1/uval_window + 1/0.7)
    # Material['Window']['UFactor'] = uval_window
    # Facade_U0value = {'0': 1.1, '1939':0.75, '1960':0.7, '1970':0.63, '1976':0.55, '1985':0.35, '2000':0.2}
    # DesiredThicknessWall = {'0': 0.045, '1939':0.066, '1960':0.071, '1970':0.079, '1976':0.09, '1985':0.14, '2000':0.25}
    # Template_W = sorted([item for item in Facade_U0value if float(item) <= year], reverse=True)[0]
    # thickness = DesiredThicknessWall[Template_W] #+ 0.05

    # Material['Wall Insulation']['Thickness'] = thickness

    if Ret['ToRet']:
        for key in MaterialUpgrade:
            Name = key
            create_MaterialObject(idf, Name, MaterialUpgrade[key])
    else:
        for key in Material:
            Name = key
            create_MaterialObject(idf, Name, Material[key])

if __name__ == '__main__' :
    print('Envelope_Param Main')