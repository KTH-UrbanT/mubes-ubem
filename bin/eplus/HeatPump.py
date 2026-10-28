# @Author  : Mohammadhossein Alizadeh
# @Email   : alizad@kth.se



# Step 1: add zone side heat delivery system

def add_water_baseboard(idf, zone_name):
    baseboard_name = f"{zone_name} Water Baseboard"

    bb = idf.newidfobject("ZONEHVAC:BASEBOARD:RADIANTCONVECTIVE:WATER")
    bb.Name = baseboard_name
    bb.Availability_Schedule_Name = "Always On"

    # These water nodes will later connect to PlantLoop demand side
    bb.Inlet_Node_Name = f"{baseboard_name} Inlet Node"
    bb.Outlet_Node_Name = f"{baseboard_name} Outlet Node"

    # Autosize for now
    bb.Heating_Design_Capacity_Method = "HeatingDesignCapacity"
    bb.Heating_Design_Capacity = "Autosize"

    bb.Fraction_Radiant = 0.3
    bb.Fraction_of_Radiant_Energy_Incident_on_People = 0.1

    return baseboard_name


def connect_baseboard_to_zone(idf, zone_name, baseboard_name):
    equip_list_name = f"{zone_name} Equipment List"

    equip_list = idf.newidfobject("ZONEHVAC:EQUIPMENTLIST")
    equip_list.Name = equip_list_name
    equip_list.Load_Distribution_Scheme = "SequentialLoad"

    equip_list.Zone_Equipment_1_Object_Type = "ZoneHVAC:Baseboard:RadiantConvective:Water"
    equip_list.Zone_Equipment_1_Name = baseboard_name
    equip_list.Zone_Equipment_1_Cooling_Sequence = 1
    equip_list.Zone_Equipment_1_Heating_or_NoLoad_Sequence = 1

    equip_conn = idf.newidfobject("ZONEHVAC:EQUIPMENTCONNECTIONS")
    equip_conn.Zone_Name = zone_name
    equip_conn.Zone_Conditioning_Equipment_List_Name = equip_list_name
    equip_conn.Zone_Air_Inlet_Node_or_NodeList_Name = f"{zone_name} Air Inlet Node"
    equip_conn.Zone_Air_Node_Name = f"{zone_name} Air Node"
    equip_conn.Zone_Return_Air_Node_or_NodeList_Name = f"{zone_name} Return Air Node"




for zone in idf.idfobjects["ZONE"]:
    zone_name = zone.Name
    baseboard_name = add_water_baseboard(idf, zone_name)
    connect_baseboard_to_zone(idf, zone_name, baseboard_name)





# Step2:

# 1. create plant loop
hw_loop = makeplantloop(
    idf,
    "Hot Water Loop",
    ["HW Supply Inlet Branch",
     ["HW Supply Branch"],
     "HW Supply Outlet Branch"],

    ["HW Demand Inlet Branch",
     [f"{z.Name} Baseboard Branch" for z in idf.idfobjects["ZONE"]],
     "HW Demand Outlet Branch"]
)

# 2. connect each baseboard to demand side
for z in idf.idfobjects["ZONE"]:

    replacebranch1(
        idf,
        hw_loop,
        f"{z.Name} Baseboard Branch",
        [
            (
                "ZONEHVAC:BASEBOARD:RADIANTCONVECTIVE:WATER",
                f"{z.Name} Water Baseboard",
                "Water"
            )
        ],
        fluid="Water"
    )


# Step 3:

# 3. replace supply pipe with pump
replacebranch1(
    idf,
    hw_loop,
    "HW Supply Branch",
    [
        (
            "PUMP:VARIABLESPEED",
            "HW Pump",
            "Water"
        )
    ],
    fluid="Water"
)

pump = idf.getobject("PUMP:VARIABLESPEED", "HW Pump")
pump.Design_Maximum_Flow_Rate = "Autosize"
pump.Design_Pump_Head = 179352
pump.Design_Power_Consumption = "Autosize"
pump.Motor_Efficiency = 0.9
pump.Fraction_of_Motor_Inefficiencies_to_Fluid_Stream = 0
pump.Pump_Control_Type = "Intermittent"


# Step 4:

# 4. put pump + heat pump in supply branch
replacebranch1(
    idf,
    hw_loop,
    "HW Supply Branch",
    [
        ("PUMP:VARIABLESPEED", "HW Pump", "Water"),
        ("HEATPUMP:WATERTOWATER:EQUATIONFIT:HEATING", "GSHP Heating", "Water")
    ],
    fluid="Water"
)

hp = idf.getobject("HEATPUMP:WATERTOWATER:EQUATIONFIT:HEATING", "GSHP Heating")

hp.Rated_Load_Side_Flow_Rate = "Autosize"
hp.Rated_Source_Side_Flow_Rate = "Autosize"
hp.Rated_Heating_Capacity = "Autosize"
hp.Rated_Heating_Coefficient_of_Performance = 4.0


# Step 5 :

source_loop = makeplantloop(
    idf,
    "Ground Source Loop",

    ["GS Supply Inlet Branch",
     ["Ground HX Branch"],
     "GS Supply Outlet Branch"],

    ["GS Demand Inlet Branch",
     ["GSHP Source Branch"],
     "GS Demand Outlet Branch"]
)

replacebranch1(
    idf,
    source_loop,
    "Ground HX Branch",
    [
        ("GROUNDHEATEXCHANGER:SYSTEM", "Ground Heat Exchanger", "Water")
    ],
    fluid="Water"
)


