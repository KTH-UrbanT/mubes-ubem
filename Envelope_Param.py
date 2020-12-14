

def createNewConstruction(idf,Name,Material):
    idf.newidfobject(
        "CONSTRUCTION", Name=Name, Outside_Layer=Material
    )


def create_MaterialObject(idf, Name, ep, U ):
    if 'Window' in Name:
        idf.newidfobject(
            'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
            Name=Name,
            UFactor=U,
            Solar_Heat_Gain_Coefficient=0.7,
            Visible_Transmittance=0.8,
        )
    else:
        idf.newidfobject(
            'MATERIAL',
            Name=Name,
            Thickness=ep,
            Conductivity=ep*U,
            Roughness="Rough",
            Density=1000,
            Specific_Heat=1000,
        )
    return idf

def CreatAirwallsMat(idf):
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
        Thickness = 0.1
        U_value = Material[key]
        create_MaterialObject(idf, Name, Thickness, U_value)

