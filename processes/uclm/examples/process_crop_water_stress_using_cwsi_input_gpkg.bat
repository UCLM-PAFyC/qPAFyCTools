echo off
set PROCESS_PATH=D:/PAFyCToolsGui/20230825_Tarazona_Thermal_CWSI/output
set OSGEO4W_ROOT=C:/Program Files/QGIS 3.22.12
set TOOL=D:/PAFyCToolsGui/20230825_Tarazona_Thermal_CWSI/output/CropWaterStressIndexUsingThermalOrthomosaic.py
cd /d "%PROCESS_PATH%"
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
python %TOOL% --input_crops_frames_shp "D:/PAFyCToolsGui/20230825_Tarazona_Thermal_CWSI/input/Shape_cepas.shp" --method_segmentation kmeans --kmeans_clusters 3 --input_orthomosaic "D:/PAFyCToolsGui/20230825_Tarazona_Thermal_CWSI/input/ORT_FTA_Tarazona_P001_20230825_4258_5782_66_mm.tif" --temperature 33.10 --relative_humidity 28.7 --upper_line_coef_a 0.221000 --upper_line_coef_b 6.671 --lower_line_coef_a -2.016800 --lower_line_coef_b 2.702 --factor_to_temperature 0.010000 --output_shp "D:/PAFyCToolsGui/20230825_Tarazona_Thermal_CWSI/output/Shape_cepas_cwsi.shp" --date_from_orthomosaic_file 1 --orthomosaic_file_string_separator="_" --orthomosaic_file_date_string_position=5 --date_format=%%Y%%m%%d --date=none
