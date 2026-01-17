import os

folder_name = os.path.basename(os.path.dirname(os.path.abspath(__file__)))


schema_info = {
    "Supply Planning": {
        "with_data": os.path.join(folder_name, "supply_planning_with_data.sql"),
        "without_data": os.path.join(folder_name, "supply_planning.sql")   
    },
    "Generic Data Model": {
        "with_data": os.path.join(folder_name, "generic_data_model_with_data.sql"),
        "without_data": os.path.join(folder_name, "generic_data_model.sql") 
    }
}