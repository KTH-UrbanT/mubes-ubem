

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
    else:
        idf.newidfobject(
            'MATERIAL',
            Name=Name,
            Thickness=Material['Thickness'],
            Conductivity = Material['Conductivity'],
            Roughness = Material['Roughness'],
            Density = Material['Density'],
            Specific_Heat = Material['Specific_Heat'],
        )
    return idf

def CreatAirwallsMat(idf):
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

def create_Material(idf, Material):
    for key in Material:
        Name = key
        create_MaterialObject(idf, Name, Material[key])

if __name__ == '__main__' :
    print('Envelope_Param Main')