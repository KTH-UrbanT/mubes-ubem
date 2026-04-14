# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

#@Edited by: Mohammadhossein Alizadeh
# @Email   : alizad@kth.se

"""
This module provides helper functions for creating and managing building envelope
materials and constructions in an EnergyPlus IDF model. It automates the generation
of MATERIAL, WINDOWMATERIAL, and CONSTRUCTION objects, supports air wall materials,
and allows switching between baseline and upgraded material sets.
"""

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

def create_Material(idf, Material, BaseMaterial_RetrofitCase, Retrofit_Info):
    if Retrofit_Info['RetrofitCase']:
        if 'window' in [item.lower() for item in Retrofit_Info['RetrofitOptions']['ECMs']]:
            BaseMaterial_RetrofitCase['Window']['UFactor'] = Retrofit_Info['RetrofitOptions']['Window_U_Value2Retrofit']
        if 'wall' in [item.lower() for item in Retrofit_Info['RetrofitOptions']['ECMs']]:
            BaseMaterial_RetrofitCase['Wall Insulation']['Thickness']  = Retrofit_Info['RetrofitOptions']['Wall_Thickness2Retrofit']
        if 'roof' in [item.lower() for item in Retrofit_Info['RetrofitOptions']['ECMs']]:
            BaseMaterial_RetrofitCase['Roof Insulation']['Thickness']  = Retrofit_Info['RetrofitOptions']['Roof_Thickness2Retrofit']
        for key in BaseMaterial_RetrofitCase:
            Name = key
            create_MaterialObject(idf, Name, BaseMaterial_RetrofitCase[key])
    # when the building is not in retrofitting list
    elif not Retrofit_Info['RetrofitCase'] and Retrofit_Info['RetrofitOptions'] != '':
        for key in BaseMaterial_RetrofitCase:
            Name = key
            create_MaterialObject(idf, Name, Material[key])
    # when retrofitting mode is off
    elif Retrofit_Info['RetrofitCase'] == '':
        for key in Material:
            Name = key
            create_MaterialObject(idf, Name, Material[key])

if __name__ == '__main__' :
    print('Envelope_Param Main')