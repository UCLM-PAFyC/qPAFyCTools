# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
# Miguel Angel Moreno Hidalgo, miguelangel.moreno@uclm.es

# import optparse
import argparse
import numpy
from osgeo import gdal, osr, ogr
import sys
import os
import json
from urllib.parse import unquote
import shutil
from os.path import exists
import datetime
import glob
from math import floor, ceil, sqrt, isnan, modf, trunc
import csv
import re
import cv2 as cv
import math
import time

STRING_TO_REPLACE_STEPS = '(\d+)'
DELAY_SECONDS = 0.1

def copy_shapefile(input_shp, output_shp):
    str_error = ''
    input_base_name = os.path.splitext(os.path.basename(input_shp))[0]
    input_base_path = os.path.dirname(input_shp)
    output_base_path = os.path.dirname(output_shp)
    output_base_name = os.path.splitext(os.path.basename(output_shp))[0]
    for file in os.listdir(input_base_path):
        file_base_name = os.path.splitext(os.path.basename(file))[0]
        if file_base_name == input_base_name:
            file_extension = os.path.splitext(os.path.basename(file))[1]
            output_file = output_base_path + "/" + output_base_name + file_extension
            output_file = os.path.normcase(output_file)
            input_file = input_base_path + "/" + file
            input_file = os.path.normcase(input_file)
            try:
                shutil.copyfile(input_file, output_file)
            except EnvironmentError as e:
                str_error = "Unable to copy file. %s" % e
                return str_error
    return str_error


def julian_date(day, month, year):
    if month <= 2:  # january & february
        year = year - 1.0
        month = month + 12.0
    jd = floor(365.25 * (year + 4716.0)) + floor(30.6001 * (month + 1.0)) + 2.0
    jd = jd - floor(year / 100.0) + floor(floor(year / 100.0) / 4.0)
    jd = jd + day - 1524.5
    # jd = jd + day - 1524.5 + (utc_time)/24.
    mjd = jd - 2400000.5
    return jd, mjd


def julian_date_to_date(jd):
    jd = jd + 0.5
    F, I = modf(jd)
    I = int(I)
    A = trunc((I - 1867216.25) / 36524.25)
    if I > 2299160:
        B = I + 1 + A - trunc(A / 4.)
    else:
        B = I
    C = B + 1524
    D = trunc((C - 122.1) / 365.25)
    E = trunc(365.25 * D)
    G = trunc((C - E) / 30.6001)
    day = C - E + F - trunc(30.6001 * G)
    if G < 13.5:
        month = G - 1
    else:
        month = G - 13
    if month > 2.5:
        year = D - 4716
    else:
        year = D - 4715
    return year, month, day


def is_number(n):
    is_number = True
    try:
        num = float(n)
        # check for "nan" floats
        is_number = num == num  # or use `math.isnan(num)`
    except ValueError:
        is_number = False
    return is_number


def sortFunction(e):
    return e['value']


def process_cwsith(temperature,
                   relative_humidity,
                   upper_line_coef_a,
                   upper_line_coef_b,
                   lower_line_coef_a,
                   lower_line_coef_b,
                   output_cswi_suffix,
                   output_min_cswi_suffix,
                   output_max_cswi_suffix,
                   output_mean_temperature_suffix,
                   output_std_temperature_suffix,
                   output_nvs_temperature_suffix,
                   kmeans_clusters,
                   percentile_maximum_threshold,
                   raster_layer_file_path,
                   raster_layer_layer_index,
                   raster_layer_layer_scale,
                   raster_layer_layer_offset,
                   str_date,
                   vector_layer_file_path,
                   vector_layer_layer_name,
                   vector_layer_enabled_field_field_name,
                   string_to_publish_number_of_steps,
                   string_to_publish_completed_steps_percentage):
    str_error = None
    if kmeans_clusters < 0 and percentile_maximum_threshold < 0:
        str_error = "Function process"
        str_error += "\nkmeans_clusters or percentile_maximum_threshold must be greather than 0"
        return str_error
    elif kmeans_clusters > 0 and percentile_maximum_threshold > 0:
        str_error = "Function process"
        str_error += "\nkmeans_clusters or percentile_maximum_threshold must be greather than 0"
        return str_error
    if not exists(vector_layer_file_path):
        str_error = "Function process"
        str_error += "\nNot exists file: {}".format(vector_layer_file_path)
        return str_error
    if not exists(raster_layer_file_path):
        str_error = "Function process"
        str_error += "\nNot exists file: {}".format(raster_layer_file_path)
        return str_error
    vector_filename, vector_file_extension = os.path.splitext(vector_layer_file_path)
    is_shapefile = False
    if vector_file_extension.casefold() == ('.shp').casefold():
        is_shapefile = True
    if is_shapefile and len(output_cswi_suffix) > 3:
        str_error = "Function process"
        str_error += ("\nFor shapefile field names suffix cannot be longer than three characters: {}"
                      .format(output_min_cswi_suffix))
        return str_error
    if output_min_cswi_suffix:
        if is_shapefile and len(output_min_cswi_suffix) > 3:
            str_error = "Function process"
            str_error += ("\nFor shapefile field names suffix cannot be longer than three characters: {}"
                          .format(output_min_cswi_suffix))
            return str_error
    if output_max_cswi_suffix:
        if is_shapefile and len(output_max_cswi_suffix) > 3:
            str_error = "Function process"
            str_error += ("\nFor shapefile field names suffix cannot be longer than three characters: {}"
                          .format(output_max_cswi_suffix))
            return str_error
    if output_mean_temperature_suffix:
        if is_shapefile and len(output_mean_temperature_suffix) > 3:
            str_error = "Function process"
            str_error += ("\nFor shapefile field names suffix cannot be longer than three characters: {}"
                          .format(output_mean_temperature_suffix))
            return str_error
    if output_std_temperature_suffix:
        if is_shapefile and len(output_std_temperature_suffix) > 3:
            str_error = "Function process"
            str_error += ("\nFor shapefile field names suffix cannot be longer than three characters: {}"
                          .format(output_std_temperature_suffix))
            return str_error
    if output_nvs_temperature_suffix:
        if is_shapefile and len(output_nvs_temperature_suffix) > 3:
            str_error = "Function process"
            str_error += ("\nFor shapefile field names suffix cannot be longer than three characters: {}"
                          .format(output_nvs_temperature_suffix))
            return str_error
    raster_ds = None
    try:
        raster_ds = gdal.Open(raster_layer_file_path)
    except ValueError:
        str_error = "Function process"
        str_error += "\nError opening dataset file:\n{}".format(raster_layer_file_path)
        return str_error
    # orthomosaic_number_of_bands = raster_ds.GetRasterCount()
    # if orthomosaic_number_of_bands != 1:
    #     str_error = "Function process"
    #     str_error += "\nOrthomosaic number of bands must be 1"
    #     return str_error
    raster_ds_rb = None
    try:
        raster_ds_rb = raster_ds.GetRasterBand(raster_layer_layer_index)
    except Exception as e:
        str_error = "Function process"
        str_error += ("\nError getting raster band: {} from file:\n{}"
                      .format(str(raster_layer_layer_index), raster_layer_file_path))
        str_error += '\nGDAL Error: ' + e.args[0]
        return str_error
    raster_geotransform = raster_ds.GetGeoTransform()
    raster_crs = osr.SpatialReference()
    raster_crs.ImportFromWkt(raster_ds.GetProjectionRef())
    raster_crs_wkt = raster_crs.ExportToWkt()
    ulx, xres, xskew, uly, yskew, yres = raster_ds.GetGeoTransform()
    lrx = ulx + (raster_ds.RasterXSize * xres)
    lry = uly + (raster_ds.RasterYSize * yres)
    out_ring = ogr.Geometry(ogr.wkbLinearRing)
    out_ring.AddPoint(ulx, uly)
    out_ring.AddPoint(lrx, uly)
    out_ring.AddPoint(lrx, lry)
    out_ring.AddPoint(ulx, lry)
    out_ring.AddPoint(ulx, uly)
    raster_poly = ogr.Geometry(ogr.wkbPolygon)
    raster_poly.AddGeometry(out_ring)
    rs_pixel_width = raster_geotransform[1]
    rs_pixel_height = raster_geotransform[5]
    raster_pixel_area = abs(rs_pixel_width) * abs(rs_pixel_height)
    raster_x_origin = raster_geotransform[0]
    raster_y_origin = raster_geotransform[3]
    raster_pixel_width = raster_geotransform[1]
    raster_pixel_height = raster_geotransform[5]
    vec_ds = None
    try:
        vec_ds = ogr.Open(vector_layer_file_path, 1)
    except Exception as e:
        str_error = "Function process"
        str_error += "\nError opening dataset file:\n{}".format(vector_layer_file_path)
        str_error += '\nGDAL Error: ' + e.args[0]
        return str_error
    vector_layer = None
    try:
        vector_layer = vec_ds.GetLayer(vector_layer_layer_name)
    except Exception as e:
        str_error = "Function process"
        str_error += ("\nError getting layer name: {} in dataset file:\n{}"
                      .format(vector_layer_layer_name, vector_layer_file_path))
        str_error = 'GDAL Error: ' + e.args[0]
        return str_error
    if not vector_layer:
        str_error = "Function process"
        str_error += ("\nError getting layer name: {} in dataset file:\n{}"
                      .format(vector_layer_layer_name, vector_layer_file_path))
        return str_error
    vector_crs = vector_layer.GetSpatialRef()
    vector_crs_wkt = vector_crs.ExportToWkt()
    vector_layer_geometry_type = vector_layer.GetGeomType()
    if vector_layer_geometry_type != ogr.wkbPolygon and vector_layer_geometry_type != ogr.wkbMultiPolygon \
            and vector_layer_geometry_type != ogr.wkbPolygonM and vector_layer_geometry_type != ogr.wkbPolygonZM \
            and vector_layer_geometry_type != ogr.wkbPolygon25D and vector_layer_geometry_type != ogr.wkbMultiPolygon25D:
        str_error = "Function process"
        str_error += "\nNot Polygon geometry type in file:\n{}".format(vector_layer_file_path)
        return str_error
    in_layer_definition = vector_layer.GetLayerDefn()
    number_of_features = vector_layer.GetFeatureCount()
    input_values = []
    position_in_input_values_by_feature_position = {}
    vector_layer_enabled_field_id_index = -1
    if vector_layer_enabled_field_field_name:
        vector_layer_enabled_field_id_index = in_layer_definition.GetFieldIndex(vector_layer_enabled_field_field_name)
        if vector_layer_enabled_field_id_index == -1:
            str_error = "Function process"
            str_error += ("\nNot enabled field: {} in layer: {} in vector file:\n{}"
                          .format(vector_layer_enabled_field_field_name, vector_layer_layer_name,
                                  vector_layer_file_path))
            return str_error
    output_field_name_tm = None
    output_field_tm_id_index = -1
    if output_mean_temperature_suffix:
        output_field_name_tm = str_date
        output_field_name_tm = output_field_name_tm + output_mean_temperature_suffix
        if kmeans_clusters > -1:
            output_field_name_tm = output_field_name_tm + 'k'
        else:
            output_field_name_tm = output_field_name_tm + 'p'
        output_field_tm_id_index = in_layer_definition.GetFieldIndex(output_field_name_tm)
        if output_field_tm_id_index == -1:
            vector_layer.CreateField(ogr.FieldDefn(output_field_name_tm, ogr.OFTReal))#ogr.OFTReal))
    output_field_name_ts = None
    output_field_ts_id_index = -1
    if output_std_temperature_suffix:
        output_field_name_ts = str_date
        output_field_name_ts = output_field_name_ts + output_std_temperature_suffix
        if kmeans_clusters > -1:
            output_field_name_ts = output_field_name_ts + 'k'
        else:
            output_field_name_ts = output_field_name_ts + 'p'
        output_field_ts_id_index = in_layer_definition.GetFieldIndex(output_field_name_ts)
        if output_field_ts_id_index == -1:
            vector_layer.CreateField(ogr.FieldDefn(output_field_name_ts, ogr.OFTReal))#ogr.OFTReal))
    output_field_name_nvs = None
    output_field_nvs_id_index = -1
    if output_nvs_temperature_suffix:
        output_field_name_nvs = str_date
        output_field_name_nvs = output_field_name_nvs + output_nvs_temperature_suffix
        output_field_nvs_id_index = in_layer_definition.GetFieldIndex(output_field_name_nvs)
        if output_field_nvs_id_index == -1:
            vector_layer.CreateField(ogr.FieldDefn(output_field_name_nvs, ogr.OFTInteger))#ogr.OFTReal))
    output_field_name_c = str_date
    output_field_name_c = output_field_name_c + output_cswi_suffix
    if kmeans_clusters > -1:
        output_field_name_c = output_field_name_c + 'k'
    else:
        output_field_name_c = output_field_name_c + 'p'
    output_field_c_id_index = in_layer_definition.GetFieldIndex(output_field_name_c)
    if output_field_c_id_index == -1:
        vector_layer.CreateField(ogr.FieldDefn(output_field_name_c, ogr.OFTReal))#ogr.OFTReal))
    output_field_name_cx = None
    output_field_cx_id_index = -1
    if output_max_cswi_suffix:
        output_field_name_cx = str_date
        output_field_name_cx = output_field_name_cx + output_max_cswi_suffix
        if kmeans_clusters > -1:
            output_field_name_cx = output_field_name_cx + 'k'
        else:
            output_field_name_cx = output_field_name_cx + 'p'
        output_field_cx_id_index = in_layer_definition.GetFieldIndex(output_field_name_cx)
        if output_field_cx_id_index == -1:
            vector_layer.CreateField(ogr.FieldDefn(output_field_name_cx, ogr.OFTReal))#ogr.OFTReal))
    output_field_name_cn = None
    output_field_cn_id_index = -1
    if output_min_cswi_suffix:
        output_field_name_cn = str_date
        output_field_name_cn = output_field_name_cn + output_min_cswi_suffix
        if kmeans_clusters > -1:
            output_field_name_cn = output_field_name_cn + 'k'
        else:
            output_field_name_cn = output_field_name_cn + 'p'
        output_field_cn_id_index = in_layer_definition.GetFieldIndex(output_field_name_cn)
        if output_field_cn_id_index == -1:
            vector_layer.CreateField(ogr.FieldDefn(output_field_name_cn, ogr.OFTReal))#ogr.OFTReal))
    es = (0.611 * math.exp((17.27 * temperature) / (237.3 + temperature)))
    ea = es * relative_humidity / 100.
    VPD = es - ea
    dTul = upper_line_coef_a * VPD + upper_line_coef_b
    dTll = lower_line_coef_a * VPD + lower_line_coef_b
    vector_layer.ResetReading()
    sys.stdout.write('Processing {} plants'.format(str(number_of_features)))
    sys.stdout.flush()
    time.sleep(DELAY_SECONDS)
    string_to_publish_number_of_steps = (string_to_publish_number_of_steps
                                         .replace(STRING_TO_REPLACE_STEPS, str(number_of_features)))
    sys.stdout.write(string_to_publish_number_of_steps)
    sys.stdout.flush()
    time.sleep(DELAY_SECONDS)
    cont_feature = 0
    for feature in vector_layer:
        sys.stdout.write('Processing plant: {}, of {}'.format(str(cont_feature + 1),
                                                   str(number_of_features)))
        sys.stdout.flush()
        if vector_layer_enabled_field_field_name:
            enabled_feature = feature[vector_layer_enabled_field_field_name]
            if isinstance(enabled_feature, str):
                try:
                    enabled_feature = int(enabled_feature)
                except ValueError:
                    str_error = "Function process"
                    str_error += ("\nIn feature: {}, enabled field: {} in layer: {} in vector file:\n{}"
                                  .format(str(cont_feature + 1), vector_layer_enabled_field_field_name,
                                          vector_layer_layer_name, vector_layer_file_path))
                    str_error += ("\nis not an integer value 0 or 1")
                    return str_error
            if enabled_feature < 0 or enabled_feature > 1:
                str_error = "Function process"
                str_error += ("\nIn feature: {}, enabled field: {} in layer: {} in vector file:\n{}"
                              .format(str(cont_feature + 1), vector_layer_enabled_field_field_name,
                                      vector_layer_layer_name, vector_layer_file_path))
                str_error += ("\nis not an integer value 0 or 1")
                return str_error
            if enabled_feature == 0:
                continue
        plot_geometry_full = feature.GetGeometryRef().Clone()
        crs_transform = None
        if vector_crs_wkt != raster_crs_wkt:
            crs_transform = osr.CoordinateTransformation(vector_crs, raster_crs)
        if crs_transform:
            plot_geometry_full.Transform(crs_transform)
        plot_geometry = None
        if raster_poly.Overlaps(plot_geometry_full):
            plot_geometry = plot_geometry_full.Intersection(raster_poly)
        if raster_poly.Contains(plot_geometry_full):
            plot_geometry = plot_geometry_full
        if raster_poly.Within(plot_geometry_full):
            plot_geometry = raster_poly
        if not plot_geometry:
            continue
        plot_geometry = plot_geometry_full.Intersection(raster_poly)
        plot_geometry_area = plot_geometry.GetArea()
        if plot_geometry_area < (3 * raster_pixel_area):
            continue
        geom_points_x = []
        geom_points_y = []
        geom_type_name = plot_geometry.GetGeometryName().lower()
        if "multipolygon" in geom_type_name:
            for i in range(0, plot_geometry.GetGeometryCount()):
                ring = plot_geometry.GetGeometryRef(i).GetGeometryRef(0)
                numpoints = ring.GetPointCount()
                for p in range(numpoints):
                    fc, sc, tc = ring.GetPoint(p)
                    geom_points_x.append(fc)
                    geom_points_y.append(sc)
        elif "polygon" in geom_type_name:
            ring = plot_geometry.GetGeometryRef(0)
            numpoints = ring.GetPointCount()
            for p in range(numpoints):
                fc, sc, tc = ring.GetPoint(p)
                geom_points_x.append(fc)
                geom_points_y.append(sc)
        else:
            # sys.exit("ERROR: Geometry needs to be either Polygon or Multipolygon")
            continue
        plot_geom_x_min = min(geom_points_x)
        plot_geom_x_max = max(geom_points_x)
        plot_geom_y_min = min(geom_points_y)
        plot_geom_y_max = max(geom_points_y)
        # Specify offset and rows and columns to read
        rs_x_off = int((plot_geom_x_min - raster_x_origin) / rs_pixel_width)
        rs_y_off = int((raster_y_origin - plot_geom_y_max) / rs_pixel_width)
        x_ul = raster_x_origin + rs_x_off * rs_pixel_width
        y_ul = raster_y_origin - rs_y_off * rs_pixel_width
        rs_x_count = int((plot_geom_x_max - plot_geom_x_min) / rs_pixel_width) + 1
        rs_y_count = int((plot_geom_y_max - plot_geom_y_min) / rs_pixel_width) + 1
        # Create memory target raster
        target_orthomosaic = gdal.GetDriverByName('MEM').Create('', rs_x_count, rs_y_count, 1, gdal.GDT_Byte)
        target_orthomosaic.SetGeoTransform((
            plot_geom_x_min, rs_pixel_width, 0,
            plot_geom_y_max, 0, rs_pixel_height,
        ))
        # Create for target raster the same projection as for the value raster
        raster_srs = osr.SpatialReference()
        raster_srs.ImportFromWkt(raster_ds.GetProjectionRef())
        target_orthomosaic.SetProjection(raster_srs.ExportToWkt())
        target_orthomosaic.SetProjection(raster_srs.ExportToWkt())
        feature_drv = ogr.GetDriverByName('ESRI Shapefile')
        feature_ds= feature_drv.CreateDataSource("/vsimem/memory_name.shp")
        # geometryType = plot_geometry.getGeometryType()
        feature_layer = feature_ds.CreateLayer("layer", raster_crs, geom_type=plot_geometry.GetGeometryType())
        featureDefnHeaders = feature_layer.GetLayerDefn()
        out_feature = ogr.Feature(featureDefnHeaders)
        out_feature.SetGeometry(plot_geometry)
        feature_layer.CreateFeature(out_feature)
        feature_ds.FlushCache()
        # Rasterize zone polygon to raster blue
        gdal.RasterizeLayer(target_orthomosaic, [1], feature_layer, burn_values=[1])
        feature_orthomosaic_band_mask = target_orthomosaic.GetRasterBand(1)
        feature_orthomosaic_data_mask = (feature_orthomosaic_band_mask.ReadAsArray(0, 0,
                                                                                  rs_x_count, rs_y_count)
                                         .astype(float))
        # Mask zone of raster blue
        feature_raster_data = (raster_ds_rb.ReadAsArray(rs_x_off, rs_y_off, rs_x_count, rs_y_count)
                                    .astype(float))
        feature_raster_array = numpy.ma.masked_array(feature_raster_data,
                                                         numpy.logical_not(feature_orthomosaic_data_mask))
        raster_first_indexes, raster_second_indexes = feature_raster_array.nonzero()
        temperature_values = []
        crop_temperature_values = []
        for i in range(len(raster_first_indexes)):
            fi = raster_first_indexes[i]
            si = raster_second_indexes[i]
            temperature = feature_raster_array[fi][si] * raster_layer_layer_scale
            temperature_values.append(temperature)
        if kmeans_clusters > -1:
            input_values_cv = numpy.zeros([len(temperature_values), 1], dtype=numpy.float32)
            cont_value = 0
            for temperature_value in temperature_values:
                input_values_cv[cont_value][0] = temperature_values[cont_value]
                cont_value = cont_value + 1
            # Define criteria = ( type, max_iter = 10 , epsilon = 1.0 )
            # criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            criteria = (cv.TERM_CRITERIA_MAX_ITER, 100, 1.0)
            flags = cv.KMEANS_RANDOM_CENTERS
            compactness, labels, centers = cv.kmeans(input_values_cv, kmeans_clusters,
                                                     None, criteria, 10, flags)
            pos_center_min_value = -1
            center_min_value = 100000000.
            # for i in range(6):
            for i in range(kmeans_clusters):
                if centers[i] < center_min_value:
                    center_min_value = centers[i]
                    pos_center_min_value = i
            cont_value = 0
            for temperature_value in temperature_values:
                if labels[cont_value] == pos_center_min_value:
                    crop_temperature_values.append(temperature_value)
                cont_value = cont_value + 1
        else:
            temperature_values.sort(key=sortFunction)
            threshold_value = -1
            cont_value = 0
            for i in range(0, len(temperature_values)):
                crop_temperature_values.append(temperature_values[cont_value])
                cont_value = cont_value + 1
                if cont_value / len(temperature_values) > percentile_maximum_threshold:
                    threshold_value = temperature_values[cont_value-1]
                    break
        crop_temperature_mean = 0
        for crop_temperature_value in crop_temperature_values:
            crop_temperature_mean = crop_temperature_mean + crop_temperature_value
        crop_temperature_mean = crop_temperature_mean / len(crop_temperature_values)
        crop_temperature_std = 0
        if len(crop_temperature_values) > 1:
            for crop_temperature_value in crop_temperature_values:
                crop_temperature_std = crop_temperature_std + pow(crop_temperature_value - crop_temperature_mean, 2.)
            crop_temperature_std = sqrt(crop_temperature_std / (len(crop_temperature_values) - 1))
        else:
            crop_temperature_std = -1.
        dTx = crop_temperature_mean - temperature
        cwsi = (dTx - dTll) / (dTul - dTll)
        dTx_min = crop_temperature_mean - crop_temperature_std - temperature
        cwsi_min = (dTx_min - dTll) / (dTul - dTll)
        dTx_max = crop_temperature_mean + crop_temperature_std - temperature
        cwsi_max = (dTx_max - dTll) / (dTul - dTll)
        feature.SetField(output_field_name_c, cwsi)
        if output_max_cswi_suffix:
            feature.SetField(output_field_name_cx, cwsi_max)
        if output_min_cswi_suffix:
            feature.SetField(output_field_name_cn, cwsi_min)
        if output_mean_temperature_suffix:
            feature.SetField(output_field_name_tm, crop_temperature_mean)
        if output_std_temperature_suffix:
            feature.SetField(output_field_name_ts, crop_temperature_std)
        if output_nvs_temperature_suffix:
            feature.SetField(output_field_name_nvs, len(crop_temperature_values))
        vector_layer.SetFeature(feature)
        cont_feature = cont_feature + 1
        int_completed_percentage = int(cont_feature / number_of_features * 100)
        if int_completed_percentage > 0:
            str_total_completed = string_to_publish_completed_steps_percentage.replace(STRING_TO_REPLACE_STEPS,
                                                                                       str(int_completed_percentage))
            sys.stdout.write(str_total_completed)
            sys.stdout.flush()
            time.sleep(DELAY_SECONDS)
        # if cont_feature > 10:
        #     break
    vec_ds = None
    return str_error


def main():
    # ==================
    # parse command line
    # ==================
    parser = argparse.ArgumentParser()
    parser.add_argument("--temperature", dest="temperature", action="store", type=float,
                      help="Air temperature (celsius degrees)", default=None)
    parser.add_argument("--relative_humidity", dest="relative_humidity", action="store", type=float,
                      help="Relative humidity (percentage)", default=None)
    parser.add_argument("--upper_line_coef_a", dest="upper_line_coef_a", action="store", type=float,
                      help="Upper line coefficient A (slope)", default=None)
    parser.add_argument("--upper_line_coef_b", dest="upper_line_coef_b", action="store", type=float,
                      help="Upper line coefficient B (y value for x equal to 0)", default=None)
    parser.add_argument("--lower_line_coef_a", dest="lower_line_coef_a", action="store", type=float,
                      help="Lower line coefficient A (slope)", default=None)
    parser.add_argument("--lower_line_coef_b", dest="lower_line_coef_b", action="store", type=float,
                      help="Lower line coefficient B (y value for x equal to 0)", default=None)
    parser.add_argument("--output_cswi_suffix", dest="output_cswi_suffix", action="store", type=str,
                      help="Output cswi suffix", default=None)
    parser.add_argument("--output_min_cswi_suffix", dest="output_min_cswi_suffix", action="store",
                        type=str, help="Output minimum cswi suffix (optional)", default=None)
    parser.add_argument("--output_max_cswi_suffix", dest="output_max_cswi_suffix", action="store",
                        type=str, help="Output maximum cswi suffix (optional)", default=None)
    parser.add_argument("--output_mean_temperature_suffix", dest="output_mean_temperature_suffix",
                        action="store", type=str, help="Output mean temperature suffix (optional)", default=None)
    parser.add_argument("--output_std_temperature_suffix", dest="output_std_temperature_suffix",
                        action="store", type=str, help="Output standard deviation temperature suffix (optional)",
                        default=None)
    parser.add_argument("--output_nvs_temperature_suffix", dest="output_nvs_temperature_suffix",
                        action="store", type=str, help="Output number of valid values of temperature suffix (optional)", default=None)
    parser.add_argument("--segmentation_method", dest="segmentation_method", action="store", type=str,
                      help="Method segmentation: kmeans or percentile", default=None)
    parser.add_argument("--kmeans_clusters (needed for kmeans segmentation method)", dest="kmeans_clusters",
                        action="store", type=int, help="Number of cluster for kmeans segmentation", default=None)
    parser.add_argument("--percentile_maximum_threshold", dest="percentile_maximum_threshold",
                        action="store", type=float, help="Maximum value (per unit) for percentile segmentation "
                                                         "(needed for percentile segmentation method)", default=None)
    parser.add_argument("--raster_layer", dest="raster_layer", action="store", type=json.loads,
                        help="raster layer dictionary: file path, layer index (int, starting 1), "
                             "scale (float) and offset (float)", default=None)
    parser.add_argument("--date_from_input_raster_file", dest="date_from_input_raster_file",
                        action="store", type=int, help="Read date from input raster file name: 1-yes, 0-No",
                        default=None)
    parser.add_argument("--date_format", dest="date_format", action="store", type=str,
                        help="Date format (%Y%m%d, ...)", default=None)
    parser.add_argument("--date", dest="date", action="store", type=str,
                        help="Needed if no read from raster file name, example: 20250624", default=None)
    parser.add_argument("--input_raster_file_tags_string_separator",
                        dest="input_raster_file_tags_string_separator", action="store", type=str,
                        help="Input raster layer file string separator", default=None)
    parser.add_argument("--input_raster_file_date_string_position",
                        dest="input_raster_file_date_string_position", action="store", type=int,
                        help="Input raster layer file date string position, for ndvi method", default=None)
    parser.add_argument("--vector_layer", dest="vector_layer", action="store", type=json.loads,
                        help="vector layer dictionary: file path, layer name, "
                             "layer geometry type (a list of valid types)", default=None)
    parser.add_argument("--vector_layer_enabled_field", dest="vector_layer_enabled_field", action="store",
                        type=json.loads, help="vector layer field dictionary: file path, layer name, "
                                              "layer geometry type (a list of valid types) and field name", default=None)
    parser.add_argument("--string_to_publish_number_of_steps", dest="string_to_publish_number_of_steps",
                        action="store", type=str, help="String to publish the number of steps", default=None)
    parser.add_argument("--string_to_publish_completed_steps_percentage",
                        dest="string_to_publish_completed_steps_percentage", action="store", type=str,
                        help="String to publish the completed steps percentage", default=None)

    args = parser.parse_args()
    if not args.temperature:
        parser.print_help()
        return
    temperature = args.temperature
    if not args.relative_humidity:
        parser.print_help()
        return
    relative_humidity = args.relative_humidity
    if not args.upper_line_coef_a:
        parser.print_help()
        return
    upper_line_coef_a = args.upper_line_coef_a
    if not args.upper_line_coef_b:
        parser.print_help()
        return
    upper_line_coef_b = args.upper_line_coef_b
    if not args.lower_line_coef_a:
        parser.print_help()
        return
    lower_line_coef_a = args.lower_line_coef_a
    if not args.lower_line_coef_b:
        parser.print_help()
        return
    lower_line_coef_b = args.lower_line_coef_b
    if not args.output_cswi_suffix:
        parser.print_help()
        return
    output_cswi_suffix = args.output_cswi_suffix
    output_min_cswi_suffix = None
    if args.output_min_cswi_suffix:
        output_min_cswi_suffix = args.output_min_cswi_suffix
    output_max_cswi_suffix = None
    if args.output_max_cswi_suffix:
        output_max_cswi_suffix = args.output_max_cswi_suffix
    output_mean_temperature_suffix = None
    if args.output_mean_temperature_suffix:
        output_mean_temperature_suffix = args.output_mean_temperature_suffix
    output_std_temperature_suffix = None
    if args.output_std_temperature_suffix:
        output_std_temperature_suffix = args.output_std_temperature_suffix
    output_nvs_temperature_suffix = None
    if args.output_nvs_temperature_suffix:
        output_nvs_temperature_suffix = args.output_nvs_temperature_suffix
    if not args.segmentation_method:
        parser.print_help()
        return
    segmentation_method = args.segmentation_method
    kmeans_clusters = -1
    percentile_maximum_threshold = -1.
    if segmentation_method == 'kmeans':
        if not args.kmeans_clusters:
            parser.print_help()
            return
        kmeans_clusters = args.kmeans_clusters
        if kmeans_clusters < 2:
            sys.stderr.write("Error:\nInvalid value for kmeans number of clusters: {}".
                  format(str(kmeans_clusters)))
            sys.stderr.flush()
            return
    elif segmentation_method == 'percentile':
        if not args.percentile_maximum_threshold:
            parser.print_help()
            return
        percentile_maximum_threshold = args.percentile_maximum_threshold
        if percentile_maximum_threshold < 0 or percentile_maximum_threshold > 1:
            sys.stderr.write("Error:\nInvalid value for percentile maximum threshold: {}".
                  format(str(percentile_maximum_threshold)))
            sys.stderr.flush()
            return
    if kmeans_clusters < 0 and percentile_maximum_threshold < 0:
        sys.stderr.write("Error:\nMethod segmentation must be: kmeans or percentile")
        sys.stderr.flush()
        return
    if not args.raster_layer:
        parser.print_help()
        return
    str_raster_layer = args.raster_layer
    # raster_layer = {}
    if not 'file_path' in str_raster_layer:
        sys.stderr.write("Error:\nNo file path in raster layer argument")
        sys.stderr.flush()
        return
    raster_layer_file_path = str_raster_layer['file_path']
    if not os.path.isfile(raster_layer_file_path):
        sys.stderr.write("Error:\nFile path in raster layer argument is not a file")
        sys.stderr.flush()
        return
    if not os.path.exists(raster_layer_file_path):
        sys.stderr.write("Error:\nFile path in raster layer argument not exists")
        sys.stderr.flush()
        return
    if not 'layer_index' in str_raster_layer:
        sys.stderr.write("Error:\nNo raster index in raster layer argument")
        sys.stderr.flush()
        return
    raster_layer_layer_index = str_raster_layer['layer_index']
    if not isinstance(raster_layer_layer_index, int):
        sys.stderr.write("Error:\nRaster index in raster layer argument is not an integer")
        sys.stderr.flush()
        return
    if raster_layer_layer_index < 1:
        sys.stderr.write("Error:\nRaster index in raster layer argument is not a valid integer")
        sys.stderr.flush()
        return
    if not 'scale' in str_raster_layer:
        sys.stderr.write("Error:\nNo scale in raster layer argument")
        sys.stderr.flush()
        return
    raster_layer_layer_scale = str_raster_layer['scale']
    if not isinstance(raster_layer_layer_scale, float):
        sys.stderr.write("Error:\nScale in raster layer argument is not a float")
        sys.stderr.flush()
        return
    if raster_layer_layer_scale < 0:
        sys.stderr.write("Error:\nScale in raster layer argument is negative")
        sys.stderr.flush()
        return
    if not 'offset' in str_raster_layer:
        sys.stderr.write("Error:\nNo offset in raster layer argument")
        sys.stderr.flush()
        return
    raster_layer_layer_offset = str_raster_layer['offset']
    if not isinstance(raster_layer_layer_offset, float):
        sys.stderr.write("Error:\nOffset in raster layer argument is not a float")
        sys.stderr.flush()
        return
    # if raster_layer_layer_offset < 0:
    #     sys.stderr.write("Error:\nOffset in raster layer argument is negative")
    #     sys.stderr.flush()
    #     return
    if not args.date_from_input_raster_file:
        parser.print_help()
        return
    date_from_input_raster_file = False
    if args.date_from_input_raster_file == 1:
        date_from_input_raster_file = True
    if not args.date_format:
        parser.print_help()
        return
    date_format = args.date_format.strip()
    date = None
    if not date_from_input_raster_file:
        if not args.date:
            sys.stderr.write("Error:\nArgument Date is needed if not read from input raster layer file name")
            sys.stderr.flush()
            return
        str_date = args.date
        is_date = True
        if len(args.date) == 6:
            str_date = '20' + str_date
        try:
            date = datetime.datetime.strptime(str_date, date_format)
        except ValueError as error:
            is_date = False
        if not is_date:
            sys.stderr.write("Error:\nInvalid string date from orthomosaic name: {} and format: {}".
                  format(args.date, date_format))
            sys.stderr.flush()
            return
    else:
        if not args.input_raster_file_tags_string_separator:
            parser.print_help()
            return
        input_raster_layer_file_string_separator = args.input_raster_file_tags_string_separator
        if not args.input_raster_file_date_string_position:
            parser.print_help()
            return
        input_raster_layer_file_date_string_position = args.input_raster_file_date_string_position
        input_raster_layer_file_name_without_path = os.path.splitext(os.path.basename(raster_layer_file_path))[0]
        input_raster_layer_file_name_values = (input_raster_layer_file_name_without_path
                                               .split(input_raster_layer_file_string_separator))
        if (input_raster_layer_file_date_string_position < 0
                or input_raster_layer_file_date_string_position > len(input_raster_layer_file_name_values)):
            sys.stderr.write("Error:\nInvalid value for input raster layer files date string position: {}".
                  format(str(input_raster_layer_file_date_string_position)))
            sys.stderr.flush()
            return
        str_date = input_raster_layer_file_name_values[input_raster_layer_file_date_string_position - 1]
        is_date = True
        if len(str_date) == 6:
            str_date = '20' + str_date
        try:
            date = datetime.datetime.strptime(str_date, date_format)
        except ValueError as error:
            is_date = False
        if not is_date:
            sys.stderr.write("Error:\nInvalid string date from input raster layer name: {} and format: {}".
                  format(input_raster_layer_file_name_values[input_raster_layer_file_date_string_position - 1],
                         date_format))
            sys.stderr.flush()
            return
    str_date = str(date.strftime('%Y')[2:4]) + str(date.strftime('%m')) + str(date.strftime('%d'))
    if not args.vector_layer:
        parser.print_help()
        return
    str_vector_layer = args.vector_layer
    # vector_layer = {}
    if not 'file_path' in str_vector_layer:
        sys.stderr.write("Error:\nNo file path in vector layer argument")
        sys.stderr.flush()
        return
    vector_layer_file_path = str_vector_layer['file_path']
    if not os.path.isfile(vector_layer_file_path):
        sys.stderr.write("Error:\nFile path in vector layer argument is not a file")
        sys.stderr.flush()
        return
    if not os.path.exists(vector_layer_file_path):
        sys.stderr.write("Error:\nFile path in vector layer argument not exists")
        sys.stderr.flush()
        return
    if not 'layer_name' in str_vector_layer:
        sys.stderr.write("Error:\nNo layer name in vector layer argument")
        sys.stderr.flush()
        return
    vector_layer_layer_name = str_vector_layer['layer_name']
    if not isinstance(vector_layer_layer_name, str):
        sys.stderr.write("Error:\nLayer name in vector layer argument is not a string")
        sys.stderr.flush()
        return
    if not 'layer_geometry_type' in str_vector_layer:
        sys.stderr.write("Error:\nNo layer geometry type in vector layer argument")
        sys.stderr.flush()
        return
    vector_layer_geometry_type = str_vector_layer['layer_geometry_type']
    if not isinstance(vector_layer_geometry_type, list):
        sys.stderr.write("Error:\nLayer geometry type in vector layer argument is not a list")
        sys.stderr.flush()
        return
    vector_layer_enabled_field_field_name = None
    if args.vector_layer_enabled_field:
        str_vector_layer_enabled_field = args.vector_layer_enabled_field
        # vector_layer = {}
        if not 'file_path' in str_vector_layer_enabled_field:
            sys.stderr.write("Error:\nNo file path in vector layer_enabled_field argument")
            sys.stderr.flush()
            return
        vector_layer_enabled_field_file_path = str_vector_layer_enabled_field['file_path']
        if vector_layer_enabled_field_file_path.casefold() != vector_layer_file_path.casefold():
            sys.stderr.write("Error:\nFile must be the same in arguments vector layer and vector layer_enabled_field")
            sys.stderr.flush()
            return
        if not os.path.isfile(vector_layer_file_path):
            sys.stderr.write("Error:\nFile path in vector layer_enabled_field argument is not a file")
            sys.stderr.flush()
            return
        if not os.path.exists(vector_layer_enabled_field_file_path):
            sys.stderr.write("Error:\nFile path in vector layer_enabled_field argument not exists")
            sys.stderr.flush()
            return
        if not 'layer_name' in str_vector_layer_enabled_field:
            sys.stderr.write("Error:\nNo layer name in vector layer_enabled_field argument")
            sys.stderr.flush()
            return
        vector_layer_enabled_field_layer_name = str_vector_layer_enabled_field['layer_name']
        if not isinstance(vector_layer_enabled_field_layer_name, str):
            sys.stderr.write("Error:\nLayer name in vector layer_enabled_field argument is not a string")
            sys.stderr.flush()
            return
        if vector_layer_enabled_field_layer_name.casefold() != vector_layer_layer_name.casefold():
            sys.stderr.write("Error:\nLayer name must be the same in arguments "
                             "vector layer and vector layer_enabled_field")
            sys.stderr.flush()
            return
        if not 'layer_geometry_type' in str_vector_layer_enabled_field:
            sys.stderr.write("Error:\nNo layer geometry type in vector layer_enabled_field argument")
            sys.stderr.flush()
            return
        vector_layer_enabled_field_geometry_type = str_vector_layer_enabled_field['layer_geometry_type']
        if not isinstance(vector_layer_enabled_field_geometry_type, list):
            sys.stderr.write("Error:\nLayer geometry type in vector layer_enabled_field argument is not a list")
            sys.stderr.flush()
            return
        if not 'field_name' in str_vector_layer_enabled_field:
            sys.stderr.write("Error:\nNo layer name in vector layer_enabled_field argument")
            sys.stderr.flush()
            return
        vector_layer_enabled_field_field_name = str_vector_layer_enabled_field['field_name']
        if not isinstance(vector_layer_enabled_field_field_name, str):
            sys.stderr.write("Error:\nField name in vector layer_enabled_field argument is not a string")
            sys.stderr.flush()
            return
    if not args.string_to_publish_number_of_steps:
        parser.print_help()
        return
    string_to_publish_number_of_steps = args.string_to_publish_number_of_steps.strip()
    if not STRING_TO_REPLACE_STEPS in string_to_publish_number_of_steps:
        str_error = ('No string to replace steps: {} in string to publish number of steps: {}'
                     .format(STRING_TO_REPLACE_STEPS, string_to_publish_number_of_steps))
        sys.stderr.write("Error:\n{}".format(str_error))
        sys.stderr.flush()
        return
    if not args.string_to_publish_completed_steps_percentage:
        parser.print_help()
        return
    string_to_publish_completed_steps_percentage = args.string_to_publish_completed_steps_percentage.strip()
    if not STRING_TO_REPLACE_STEPS in string_to_publish_completed_steps_percentage:
        str_error = ('No string to replace steps: {} in string to publish completed steps percentage: {}'
                     .format(STRING_TO_REPLACE_STEPS, string_to_publish_completed_steps_percentage))
        sys.stderr.write("Error:\n{}".format(str_error))
        sys.stderr.flush()
        return
    str_error = process_cwsith(temperature,
                               relative_humidity,
                               upper_line_coef_a,
                               upper_line_coef_b,
                               lower_line_coef_a,
                               lower_line_coef_b,
                               output_cswi_suffix,
                               output_min_cswi_suffix,
                               output_max_cswi_suffix,
                               output_mean_temperature_suffix,
                               output_std_temperature_suffix,
                               output_nvs_temperature_suffix,
                               kmeans_clusters,
                               percentile_maximum_threshold,
                               raster_layer_file_path,
                               raster_layer_layer_index,
                               raster_layer_layer_scale,
                               raster_layer_layer_offset,
                               str_date,
                               vector_layer_file_path,
                               vector_layer_layer_name,
                               vector_layer_enabled_field_field_name,
                               string_to_publish_number_of_steps,
                               string_to_publish_completed_steps_percentage)
    if str_error:
        sys.stderr.write("Error:\n{}".format(str_error))
        sys.stderr.flush()
        return
    # sys.stdout.write("... Process finished")
    # sys.stdout.flush()

if __name__ == '__main__':
    main()
