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

def process(crops_minimum_height,
            crops_minimum_ndvi,
            shadows_maximum_reflectance,
            segmentation_method,
            kmeans_clusters,
            output_plant_healthy_suffix,
            output_plant_ndvi_suffix,
            percentile_minimum_threshold,
            raster_layer_dsm_file_path,
            raster_layer_dsm_layer_index,
            raster_layer_dsm_layer_scale,
            raster_layer_dsm_layer_offset,
            raster_layer_dtm_file_path,
            raster_layer_dtm_layer_index,
            raster_layer_dtm_layer_scale,
            raster_layer_dtm_layer_offset,
            raster_layer_file_path,
            raster_layer_blue_band_layer_index,
            raster_layer_blue_band_layer_scale,
            raster_layer_blue_band_layer_offset,
            raster_layer_green_band_layer_index,
            raster_layer_green_band_layer_scale,
            raster_layer_green_band_layer_offset,
            raster_layer_red_band_layer_index,
            raster_layer_red_band_layer_scale,
            raster_layer_red_band_layer_offset,
            raster_layer_nir_band_layer_index,
            raster_layer_nir_band_layer_scale,
            raster_layer_nir_band_layer_offset,
            str_date,
            vector_layer_file_path,
            vector_layer_layer_name,
            vector_layer_enabled_field_field_name,
            string_to_publish_number_of_steps,
            string_to_publish_completed_steps_percentage):
    str_error = ''
    if kmeans_clusters < 0 and percentile_minimum_threshold < 0:
        str_error = "Function process"
        str_error += "\nkmeans_clusters or percentile_minimum_threshold must be greather than 0"
        return str_error
    elif kmeans_clusters > 0 and percentile_minimum_threshold > 0:
        str_error = "Function process"
        str_error += "\nkmeans_clusters or percentile_minimum_threshold must be greather than 0"
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
    if is_shapefile and len(output_plant_healthy_suffix) > 3:
        str_error = "Function process"
        str_error += ("\nFor shapefile field names suffix cannot be longer than three characters: {}"
                      .format(output_plant_healthy_suffix))
        return str_error
    if output_plant_ndvi_suffix:
        if is_shapefile and len(output_plant_ndvi_suffix) > 3:
            str_error = "Function process"
            str_error += ("\nFor shapefile field names suffix cannot be longer than three characters: {}"
                          .format(output_plant_ndvi_suffix))
            return str_error
    dsm_ds = None
    dsm_rb = None
    dsm_crs = None
    dsm_gsd_x = None
    dsm_gsd_y = None
    dsm_xSize = None
    dsm_ySize = None
    dsm_ulx = None
    dsm_uly = None
    dsm_lrx = None
    dsm_lry = None
    dsm_geotransform = None
    dsm_no_data_value = None
    dtm_ds = None
    dtm_rb = None
    dtm_crs = None
    dtm_gsd_x = None
    dtm_gsd_y = None
    dtm_xSize = None
    dtm_ySize = None
    dtm_ulx = None
    dtm_uly = None
    dtm_lrx = None
    dtm_lry = None
    dtm_geotransform = None
    dsm_no_data_value = None
    dtm_no_data_value = None
    if crops_minimum_height > 0.0:# or crop_minimum_height < -0.001:
        if not exists(raster_layer_dsm_file_path):
            str_error = "Function process"
            str_error += "\nNot exists file: {}".format(raster_layer_dsm_file_path)
            return str_error
        if not exists(raster_layer_dtm_file_path):
            str_error = "Function process"
            str_error += "\nNot exists file: {}".format(raster_layer_dtm_file_path)
            return str_error
        try:
            dsm_ds = gdal.Open(raster_layer_dsm_file_path)
        except ValueError:
            str_error = "Function process"
            str_error += "\nError opening dataset file:\n{}".format(raster_layer_dsm_file_path)
            return str_error
        try:
            dsm_rb = dsm_ds.GetRasterBand(1)
        except ValueError:
            str_error = "Function process"
            str_error += "\nError getting raster band from file:\n{}".format(raster_layer_dsm_file_path)
            return str_error
        try:
            dtm_ds = gdal.Open(raster_layer_dtm_file_path)
        except ValueError:
            str_error = "Function process"
            str_error += "\nError opening dataset file:\n{}".format(raster_layer_dtm_file_path)
            return str_error
        try:
            dtm_rb = dtm_ds.GetRasterBand(1)
        except ValueError:
            str_error = "Function process"
            str_error += "\nError getting raster band from file:\n{}".format(raster_layer_dtm_file_path)
            return str_error
        dsm_crs = osr.SpatialReference()
        dsm_crs.ImportFromWkt(dsm_ds.GetProjectionRef())
        dsm_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        dsm_crs_wkt = dsm_crs.ExportToWkt()
        dsm_xSize = dsm_ds.RasterXSize
        dsm_ySize = dsm_ds.RasterYSize
        dsm_geotransform = dsm_ds.GetGeoTransform()
        dsm_gsd_x = abs(dsm_geotransform[1])
        dsm_gsd_y = abs(dsm_geotransform[5])
        dsm_ulx, dsm_xres, dsm_xskew, dsm_uly, dsm_yskew, dsm_yres = dsm_ds.GetGeoTransform()
        dsm_lrx = dsm_ulx + (dsm_ds.RasterXSize * dsm_xres)
        dsm_lry = dsm_uly + (dsm_ds.RasterYSize * dsm_yres)
        dsm_no_data_value = dsm_rb.GetNoDataValue()
        dtm_crs = osr.SpatialReference()
        dtm_crs.ImportFromWkt(dtm_ds.GetProjectionRef())
        dtm_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        dtm_crs_wkt = dtm_crs.ExportToWkt()
        dtm_xSize = dtm_ds.RasterXSize
        dtm_ySize = dtm_ds.RasterYSize
        dtm_geotransform = dtm_ds.GetGeoTransform()
        dtm_gsd_x = abs(dtm_geotransform[1])
        dtm_gsd_y = abs(dtm_geotransform[5])
        dtm_ulx, dtm_xres, dtm_xskew, dtm_uly, dtm_yskew, dtm_yres = dtm_ds.GetGeoTransform()
        dtm_lrx = dtm_ulx + (dtm_ds.RasterXSize * dtm_xres)
        dtm_lry = dtm_uly + (dtm_ds.RasterYSize * dtm_yres)
        dtm_no_data_value = dtm_rb.GetNoDataValue()
    orthomosaic_ds = None
    try:
        orthomosaic_ds = gdal.Open(raster_layer_file_path)
    except ValueError:
        str_error = "Function process"
        str_error += "\nError opening dataset file:\n{}".format(raster_layer_file_path)
        return str_error
    orthomosaic_number_of_bands =orthomosaic_ds.RasterCount
    if raster_layer_blue_band_layer_index < 1 or raster_layer_blue_band_layer_index > orthomosaic_number_of_bands:
        str_error = "Function process"
        str_error += ("\nBlue band position is out of domain of bands in file:\n{}".format(raster_layer_file_path))
        return str_error
    if raster_layer_green_band_layer_index < 1 or raster_layer_green_band_layer_index > orthomosaic_number_of_bands:
        str_error = "Function process"
        str_error += ("\nGreen band position is out of domain of bands in file:\n{}".format(raster_layer_file_path))
        return str_error
    if raster_layer_red_band_layer_index < 1 or raster_layer_red_band_layer_index > orthomosaic_number_of_bands:
        str_error = "Function process"
        str_error += ("\nRed band position is out of domain of bands in file:\n{}".format(raster_layer_file_path))
        return str_error
    if raster_layer_nir_band_layer_index < 1 or raster_layer_nir_band_layer_index > orthomosaic_number_of_bands:
        str_error = "Function process"
        str_error += ("\nNir band position is out of domain of bands in file:\n{}".format(raster_layer_file_path))
        return str_error
    orthomosaic_ds_rb_blue = None
    try:
        orthomosaic_ds_rb_blue = orthomosaic_ds.GetRasterBand(raster_layer_blue_band_layer_index)
    except ValueError:
        str_error = "Function process"
        str_error += "\nError getting BLUE raster band from file:\n{}".format(raster_layer_file_path)
        return str_error
    orthomosaic_rb_blue_no_data_value = orthomosaic_ds_rb_blue.GetNoDataValue()
    orthomosaic_ds_rb_green = None
    try:
        orthomosaic_ds_rb_green = orthomosaic_ds.GetRasterBand(raster_layer_green_band_layer_index)
    except ValueError:
        str_error = "Function process"
        str_error += "\nError getting GREEN raster band from file:\n{}".format(raster_layer_file_path)
        return str_error
    orthomosaic_rb_green_no_data_value = orthomosaic_ds_rb_green.GetNoDataValue()
    orthomosaic_ds_rb_red = None
    try:
        orthomosaic_ds_rb_red = orthomosaic_ds.GetRasterBand(raster_layer_red_band_layer_index)
    except ValueError:
        str_error = "Function process"
        str_error += "\nError getting RED raster band from file:\n{}".format(raster_layer_file_path)
        return str_error
    orthomosaic_rb_red_no_data_value = orthomosaic_ds_rb_red.GetNoDataValue()
    orthomosaic_ds_rb_nir = None
    try:
        orthomosaic_ds_rb_nir = orthomosaic_ds.GetRasterBand(raster_layer_nir_band_layer_index)
    except ValueError:
        str_error = "Function process"
        str_error += "\nError getting NIR raster band from file:\n{}".format(raster_layer_file_path)
        return str_error
    orthomosaic_rb_nir_no_data_value = orthomosaic_ds_rb_nir.GetNoDataValue()
    xSize = orthomosaic_ds.RasterXSize
    ySize = orthomosaic_ds.RasterYSize
    orthomosaic_geotransform = orthomosaic_ds.GetGeoTransform()
    gsd_x = abs(orthomosaic_geotransform[1])
    gsd_y = abs(orthomosaic_geotransform[5])
    gsd = gsd_x
    projection = orthomosaic_ds.GetProjection()
    orthomosaic_crs = osr.SpatialReference()
    transform_crs_orthomosaic_to_dsm = None
    transform_crs_orthomosaic_to_dtm = None
    orthomosaic_crs.ImportFromWkt(orthomosaic_ds.GetProjectionRef())
    orthomosaic_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if crops_minimum_height > 0.0:
        transform_crs_orthomosaic_to_dsm = osr.CoordinateTransformation(orthomosaic_crs, dsm_crs)
        transform_crs_orthomosaic_to_dtm = osr.CoordinateTransformation(orthomosaic_crs, dtm_crs)
    orthomosaic_crs_wkt = orthomosaic_crs.ExportToWkt()
    ulx, xres, xskew, uly, yskew, yres = orthomosaic_ds.GetGeoTransform()
    lrx = ulx + (orthomosaic_ds.RasterXSize * xres)
    lry = uly + (orthomosaic_ds.RasterYSize * yres)
    out_ring = ogr.Geometry(ogr.wkbLinearRing)
    out_ring.AddPoint(ulx, uly)
    out_ring.AddPoint(lrx, uly)
    out_ring.AddPoint(lrx, lry)
    out_ring.AddPoint(ulx, lry)
    out_ring.AddPoint(ulx, uly)
    orthomosaic_poly = ogr.Geometry(ogr.wkbPolygon)
    orthomosaic_poly.AddGeometry(out_ring)
    rs_pixel_width = orthomosaic_geotransform[1]
    rs_pixel_height = orthomosaic_geotransform[5]
    orthomosaic_pixel_area = abs(rs_pixel_width) * abs(rs_pixel_height)
    orthomosaic_x_origin = orthomosaic_geotransform[0]
    orthomosaic_y_origin = orthomosaic_geotransform[3]
    orthomosaic_pixel_width = orthomosaic_geotransform[1]
    orthomosaic_pixel_height = orthomosaic_geotransform[5]
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
    transform_crs_vector_to_orthomosaic = None
    transform_crs_vector_to_orthomosaic = osr.CoordinateTransformation(vector_crs, orthomosaic_crs)
    vector_layer_geometry_type = vector_layer.GetGeomType()
    if vector_layer_geometry_type != ogr.wkbPolygon and vector_layer_geometry_type != ogr.wkbMultiPolygon \
            and vector_layer_geometry_type != ogr.wkbPolygonM and vector_layer_geometry_type != ogr.wkbPolygonZM \
            and vector_layer_geometry_type != ogr.wkbPolygon25D and vector_layer_geometry_type != ogr.wkbMultiPolygon25D:
        str_error = "Function process"
        str_error += "\nNot Polygon geometry type in file:\n{}".format(vector_layer_file_path)
        return str_error
    vector_layer_definition = vector_layer.GetLayerDefn()
    number_of_features = vector_layer.GetFeatureCount()
    input_values = []
    position_in_input_values_by_feature_position = {}
    vector_layer_enabled_field_id_index = -1
    if vector_layer_enabled_field_field_name:
        vector_layer_enabled_field_id_index = vector_layer_definition.GetFieldIndex(vector_layer_enabled_field_field_name)
        if vector_layer_enabled_field_id_index == -1:
            str_error = "Function process"
            str_error += ("\nNot enabled field: {} in layer: {} in vector file:\n{}"
                          .format(vector_layer_enabled_field_field_name, vector_layer_layer_name,
                                  vector_layer_file_path))
            return str_error
    output_field_name_healthy = str_date
    output_field_name_healthy = output_field_name_healthy + output_plant_healthy_suffix
    if kmeans_clusters > -1:
        output_field_name_healthy = output_field_name_healthy + 'k'
    else:
        output_field_name_healthy = output_field_name_healthy + 'p'
    output_field_healthy_id_index = vector_layer_definition.GetFieldIndex(output_field_name_healthy)
    if output_field_healthy_id_index == -1:
        vector_layer.CreateField(ogr.FieldDefn(output_field_name_healthy, ogr.OFTInteger))#ogr.OFTReal))4
    output_field_ndvi_id_index = -1
    output_field_name_ndvi = ''
    if output_plant_ndvi_suffix:
        output_field_name_ndvi = str_date
        output_field_name_ndvi = output_field_name_ndvi + output_plant_ndvi_suffix
        if kmeans_clusters > -1:
            output_field_name_ndvi = output_field_name_ndvi + 'k'
        else:
            output_field_name_ndvi = output_field_name_ndvi + 'p'
        output_field_ndvi_id_index = vector_layer_definition.GetFieldIndex(output_field_name_ndvi)
        if output_field_ndvi_id_index == -1:
            vector_layer.CreateField(ogr.FieldDefn(output_field_name_ndvi, ogr.OFTReal))  # ogr.OFTReal))4
    vector_layer.ResetReading()
    sys.stdout.write('First step: processing {} plants'.format(str(number_of_features)))
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
        plot_geometry_full.Transform(transform_crs_vector_to_orthomosaic)
        plot_geometry = None
        if orthomosaic_poly.Overlaps(plot_geometry_full):
            plot_geometry = plot_geometry_full.Intersection(orthomosaic_poly)
        if orthomosaic_poly.Contains(plot_geometry_full):
            plot_geometry = plot_geometry_full
        if orthomosaic_poly.Within(plot_geometry_full):
            plot_geometry = orthomosaic_poly
        if not plot_geometry:
            cont_feature = cont_feature + 1
            continue
        plot_geometry = plot_geometry_full.Intersection(orthomosaic_poly)
        plot_geometry_area = plot_geometry.GetArea()
        if plot_geometry_area < (3 * orthomosaic_pixel_area):
            cont_feature = cont_feature + 1
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
            cont_feature = cont_feature + 1
            continue
        plot_geom_x_min = min(geom_points_x)
        plot_geom_x_max = max(geom_points_x)
        plot_geom_y_min = min(geom_points_y)
        plot_geom_y_max = max(geom_points_y)
        # Specify offset and rows and columns to read
        rs_x_off = int((plot_geom_x_min - orthomosaic_x_origin) / rs_pixel_width)
        rs_y_off = int((orthomosaic_y_origin - plot_geom_y_max) / rs_pixel_width)
        x_ul = orthomosaic_x_origin + rs_x_off * rs_pixel_width
        y_ul = orthomosaic_y_origin - rs_y_off * rs_pixel_width
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
        raster_srs.ImportFromWkt(orthomosaic_ds.GetProjectionRef())
        target_orthomosaic.SetProjection(raster_srs.ExportToWkt())
        target_orthomosaic.SetProjection(raster_srs.ExportToWkt())
        feature_drv = ogr.GetDriverByName('ESRI Shapefile')
        feature_ds = feature_drv.CreateDataSource("/vsimem/memory_name.shp")
        # geometryType = plot_geometry.getGeometryType()
        feature_layer = feature_ds.CreateLayer("layer", orthomosaic_crs, geom_type = plot_geometry.GetGeometryType())
        featureDefnHeaders = feature_layer.GetLayerDefn()
        out_feature = ogr.Feature(featureDefnHeaders)
        out_feature.SetGeometry(plot_geometry)
        feature_layer.CreateFeature(out_feature)
        feature_ds.FlushCache()
        # Rasterize zone polygon to raster blue
        gdal.RasterizeLayer(target_orthomosaic, [1], feature_layer, burn_values=[1])
        feature_orthomosaic_band_mask = target_orthomosaic.GetRasterBand(1)
        feature_orthomosaic_data_mask = (feature_orthomosaic_band_mask.ReadAsArray(0, 0, rs_x_count, rs_y_count).astype(float))
        # Mask zone of raster blue
        feature_orthomosaic_data_blue = (orthomosaic_ds_rb_blue.ReadAsArray(rs_x_off, rs_y_off, rs_x_count, rs_y_count).astype(float))
        feature_raster_array_blue = numpy.ma.masked_array(feature_orthomosaic_data_blue, numpy.logical_not(feature_orthomosaic_data_mask))
        orthomosaic_first_indexes_blue, orthomosaic_second_indexes_blue = feature_raster_array_blue.nonzero()
        # Mask zone of raster green
        feature_orthomosaic_data_green = (orthomosaic_ds_rb_green.ReadAsArray(rs_x_off, rs_y_off, rs_x_count, rs_y_count).astype(float))
        feature_raster_array_green = numpy.ma.masked_array(feature_orthomosaic_data_green, numpy.logical_not(feature_orthomosaic_data_mask))
        orthomosaic_first_indexes_green, orthomosaic_second_indexes_green = feature_raster_array_green.nonzero()
        # Mask zone of raster red
        feature_orthomosaic_data_red = (orthomosaic_ds_rb_red.ReadAsArray(rs_x_off, rs_y_off, rs_x_count, rs_y_count).astype(float))
        feature_raster_array_red = numpy.ma.masked_array(feature_orthomosaic_data_red, numpy.logical_not(feature_orthomosaic_data_mask))
        orthomosaic_first_indexes_red, orthomosaic_second_indexes_red = feature_raster_array_red.nonzero()
        # Mask zone of raster nir
        feature_orthomosaic_data_nir = (orthomosaic_ds_rb_nir.ReadAsArray(rs_x_off, rs_y_off, rs_x_count, rs_y_count).astype(float))
        feature_raster_array_nir = numpy.ma.masked_array(feature_orthomosaic_data_nir, numpy.logical_not(feature_orthomosaic_data_mask))
        orthomosaic_first_indexes_nir, orthomosaic_second_indexes_nir = feature_raster_array_nir.nonzero()
        ndvi_mean = 0.
        ndvi_min = 2.
        ndvi_max = -2.
        ndvi_number_of_values = 0
        feature_dsm_data = None
        feature_dsm_col_off = None
        feature_dsm_row_off = None
        feature_dsm_col_count = None
        feature_dsm_row_count = None
        feature_dtm_data = None
        feature_dtm_col_off = None
        feature_dtm_row_off = None
        feature_dtm_col_count = None
        feature_dtm_row_count = None
        if crops_minimum_height > 0:
            feature_dsm_col_off = int((plot_geom_x_min - dsm_ulx) / dsm_gsd_x)
            if feature_dsm_col_off < 0:
                feature_dsm_col_off = 0
            feature_dsm_row_off = int((dsm_uly - plot_geom_y_max) / dsm_gsd_x)
            if feature_dsm_row_off < 0:
                feature_dsm_row_off = 0
            feature_dsm_x_ul = dsm_ulx + feature_dsm_col_off * dsm_gsd_x
            feature_dsm_y_ul = dsm_uly - feature_dsm_row_off * dsm_gsd_x
            feature_dsm_col_count = int((plot_geom_x_max - plot_geom_x_min) / dsm_gsd_x) + 1
            feature_dsm_row_count = int((plot_geom_y_max - plot_geom_y_min) / dsm_gsd_x) + 1
            if (feature_dsm_col_off + feature_dsm_col_count) > dsm_xSize:
                feature_dsm_col_count = dsm_xSize - feature_dsm_col_off
            if (feature_dsm_row_off + feature_dsm_row_count) > dsm_ySize:
                feature_dsm_row_count = dsm_ySize - feature_dsm_row_off
            feature_dsm_data = dsm_rb.ReadAsArray(feature_dsm_col_off, feature_dsm_row_off,
                                                  feature_dsm_col_count, feature_dsm_row_count).astype(float)
            feature_dtm_col_off = int((plot_geom_x_min - dtm_ulx) / dtm_gsd_x)
            if feature_dtm_col_off < 0:
                feature_dtm_col_off = 0
            feature_dtm_row_off = int((dtm_uly - plot_geom_y_max) / dtm_gsd_x)
            if feature_dtm_row_off < 0:
                feature_dtm_row_off = 0
            feature_dtm_x_ul = dtm_ulx + feature_dtm_col_off * dtm_gsd_x
            feature_dtm_y_ul = dtm_uly - feature_dtm_row_off * dtm_gsd_x
            feature_dtm_col_count = int((plot_geom_x_max - plot_geom_x_min) / dtm_gsd_x) + 1
            feature_dtm_row_count = int((plot_geom_y_max - plot_geom_y_min) / dtm_gsd_x) + 1
            if (feature_dtm_col_off + feature_dtm_col_count) > dtm_xSize:
                feature_dtm_col_count = dtm_xSize - feature_dtm_col_off
            if (feature_dtm_row_off + feature_dtm_row_count) > dtm_ySize:
                feature_dtm_row_count = dtm_ySize - feature_dtm_row_off
            feature_dtm_data = dtm_rb.ReadAsArray(feature_dtm_col_off, feature_dtm_row_off,
                                                  feature_dtm_col_count, feature_dtm_row_count).astype(float)
        for i in range(len(orthomosaic_first_indexes_blue)):
            fi = orthomosaic_first_indexes_blue[i]
            si = orthomosaic_second_indexes_blue[i]
            if (not fi in orthomosaic_first_indexes_green
                    or not fi in orthomosaic_first_indexes_red
                    or not fi in orthomosaic_first_indexes_nir):
                continue
            if (not si in orthomosaic_second_indexes_green
                    or not si in orthomosaic_second_indexes_red
                    or not si in orthomosaic_second_indexes_nir):
                continue
            if abs(feature_raster_array_blue[fi][si] - orthomosaic_rb_blue_no_data_value) < 1:
                continue
            if abs(feature_raster_array_green[fi][si] - orthomosaic_rb_green_no_data_value) < 1:
                continue
            if abs(feature_raster_array_red[fi][si] - orthomosaic_rb_red_no_data_value) < 1:
                continue
            if abs(feature_raster_array_nir[fi][si] - orthomosaic_rb_nir_no_data_value) < 1:
                continue
            blue = (feature_raster_array_blue[fi][si] * raster_layer_blue_band_layer_scale
                    + raster_layer_blue_band_layer_offset)
            green = (feature_raster_array_green[fi][si] * raster_layer_green_band_layer_scale
                     + raster_layer_green_band_layer_offset)
            red = (feature_raster_array_red[fi][si] * raster_layer_red_band_layer_scale
                   + raster_layer_red_band_layer_offset)
            nir = (feature_raster_array_nir[fi][si] * raster_layer_nir_band_layer_scale
                   + raster_layer_red_band_layer_offset)
            if (blue < shadows_maximum_reflectance
                    and green < shadows_maximum_reflectance
                    and red < shadows_maximum_reflectance):
                continue
            ndvi = (nir - red) / (red + nir)
            if ndvi < crops_minimum_ndvi:
                continue
            if crops_minimum_height > 0:
                rs_x = orthomosaic_x_origin + (rs_x_off + fi) * rs_pixel_width
                rs_y = orthomosaic_y_origin - (rs_y_off + si) * rs_pixel_width
                dsm_x, dsm_y, _ = transform_crs_orthomosaic_to_dsm.TransformPoint(rs_x, rs_y)
                dsm_column = math.floor((dsm_x - dsm_ulx) / dsm_gsd_x)
                feature_dsm_column = dsm_column - feature_dsm_col_off
                dsm_row = math.floor((dsm_uly - dsm_y) / dsm_gsd_y)
                feature_dsm_row = dsm_row - feature_dsm_row_off
                dsm_height = None
                if feature_dsm_column >= 0 and (feature_dsm_column - feature_dsm_col_off) < feature_dsm_col_count\
                        and feature_dsm_row >= 0 and (feature_dsm_row - feature_dsm_row_off) < feature_dsm_row_count:
                    dsm_height = feature_dsm_data[feature_dsm_row][feature_dsm_column]
                    if abs(dsm_height - dsm_no_data_value) < 1:
                        dsm_height = None
                if dsm_height:
                    dtm_x, dtm_y, _ = transform_crs_orthomosaic_to_dtm.TransformPoint(rs_x, rs_y)
                    dtm_column = math.floor((dtm_x - dtm_ulx) / dtm_gsd_x)
                    feature_dtm_column = dtm_column - feature_dtm_col_off
                    dtm_row = math.floor((dtm_uly - dtm_y) / dtm_gsd_y)
                    feature_dtm_row = dtm_row - feature_dtm_row_off
                    dtm_height = None
                    if feature_dtm_column >= 0 and (feature_dtm_column - feature_dtm_col_off) < feature_dtm_col_count \
                            and feature_dtm_row >= 0 and (
                            feature_dtm_row - feature_dtm_row_off) < feature_dtm_row_count:
                        dtm_height = feature_dtm_data[feature_dtm_row][feature_dtm_column]
                        if abs(dtm_height - dtm_no_data_value) < 1:
                            dtm_height = None
                    if dtm_height:
                        crop_height = dsm_height - dtm_height
                        if crop_height < crops_minimum_height:
                            continue
            ndvi_mean = ndvi_mean + ndvi
            if ndvi < ndvi_min:
                ndvi_min = ndvi
            if ndvi > ndvi_max:
                ndvi_max = ndvi
            ndvi_number_of_values = ndvi_number_of_values + 1
        if ndvi_number_of_values > 0:
            ndvi_mean = ndvi_mean / ndvi_number_of_values
            input_value = {}
            input_value['position'] = cont_feature
            input_value['value'] = ndvi_mean
            input_values.append(input_value)
            position_in_input_values_by_feature_position[cont_feature] = len(input_values) - 1
        else:
            ndvi_mean = -1
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
    sys.stdout.write('Second step: processing segmentation')
    sys.stdout.flush()
    time.sleep(DELAY_SECONDS)
    if len(input_values) == 0:
        str_error = "Function process"
        str_error += ("\nThere are no valid values for any plant")
        vec_ds = None
        return str_error
    if kmeans_clusters > -1:
        input_values_cv = numpy.zeros([len(input_values), 1], dtype=numpy.float32)
        cont_feature_crop = 0
        for input_value in input_values:
            input_values_cv[cont_feature_crop][0] = input_value['value']
            cont_feature_crop = cont_feature_crop + 1
        # Define criteria = ( type, max_iter = 10 , epsilon = 1.0 )
        # criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        criteria = (cv.TERM_CRITERIA_MAX_ITER, 100, 1.0)
        flags = cv.KMEANS_RANDOM_CENTERS
        compactness, labels, centers = cv.kmeans(input_values_cv, kmeans_clusters,
                                                 None, criteria, 10, flags)
        pos_center_min_value = -1
        center_min_value = 100000000.
        for i in range(kmeans_clusters):
            if centers[i] < center_min_value:
                center_min_value = centers[i]
                pos_center_min_value = i
        cont_feature = 0
        vector_layer.ResetReading()
        for feature in vector_layer:
            damaged = 0
            ndvi = -1
            if not cont_feature in position_in_input_values_by_feature_position:
                damaged = -1
            else:
                pos_in_input_values = position_in_input_values_by_feature_position[cont_feature]
                pos_center = labels[position_in_input_values_by_feature_position[cont_feature]][0]
                if pos_center == pos_center_min_value:
                    damaged = 1
                ndvi = input_values[position_in_input_values_by_feature_position[cont_feature]]['value']
            cont_feature = cont_feature + 1
            feature.SetField(output_field_name_healthy, damaged)
            if output_field_name_ndvi:
                feature.SetField(output_field_name_ndvi, ndvi)
            vector_layer.SetFeature(feature)
    else:
        input_values.sort(key=sortFunction)
        damage_positions = []
        number_of_damages = 0
        threshold_value = -1
        for i in range(0, len(input_values)):
            damage_positions.append(input_values[i]['position'])
            if number_of_damages / number_of_features > percentile_minimum_threshold:
                threshold_value = input_values[i]['value']
                break
            number_of_damages = number_of_damages + 1
        cont_feature = 0
        vector_layer.ResetReading()
        for feature in vector_layer:
            damaged = 0
            ndvi = -1
            if not cont_feature in position_in_input_values_by_feature_position:
                damaged = -1
            else:
                if cont_feature in damage_positions:
                    damaged = 1
                ndvi = input_values[position_in_input_values_by_feature_position[cont_feature]]['value']
            cont_feature = cont_feature + 1
            feature.SetField(output_field_name_healthy, damaged)
            if output_field_name_ndvi:
                feature.SetField(output_field_name_ndvi, ndvi)
            vector_layer.SetFeature(feature)
    vec_ds = None
    return str_error



def main():
    # ==================
    # parse command line
    # ==================
    parser = argparse.ArgumentParser()
    parser.add_argument("--crops_minimum_height", dest="crops_minimum_height", action="store", type=float,
                      help="Crops minimum Heights, in meters, 0 for ignore", default=None)
    parser.add_argument("--crops_minimum_ndvi", dest="crops_minimum_ndvi", action="store", type=float,
                      help="Crops minimum NDVI (per unit)", default=None)
    parser.add_argument("--shadows_maximum_reflectance", dest="shadows_maximum_reflectance", action="store",
                        type=float, help="Shadows maximum reflectance (RGB) (per unit)", default=None)
    parser.add_argument("--segmentation_method", dest="segmentation_method", action="store", type=str,
                      help="Method segmentation: kmeans or percentile", default=None)
    parser.add_argument("--kmeans_clusters (needed for kmeans segmentation method)", dest="kmeans_clusters",
                        action="store", type=int, help="Number of cluster for kmeans segmentation", default=None)
    parser.add_argument("--percentile_minimum_threshold", dest="percentile_minimum_threshold",
                        action="store", type=float, help="Minimum value (per unit) for percentile segmentation "
                                                         "(needed for percentile segmentation method)", default=None)
    parser.add_argument("--raster_layer_dsm_band", dest="raster_layer_dsm_band", action="store",
                        type=json.loads, help="Raster layer digital surface model, needed for use crops minimimum "
                                              "heigth, converted to meters using: scale * ND + offset: file path, "
                                              "layer index (int, starting 1), scale (float) "
                                              "and offset (float)", default=None)
    parser.add_argument("--raster_layer_dtm_band", dest="raster_layer_dtm_band", action="store",
                        type=json.loads, help="Raster layer digital terrain model, needed for use crops minimimum "
                                              "heigth, converted to meters using: scale * ND + offset: file path, "
                                              "layer index (int, starting 1), scale (float) "
                                              "and offset (float)", default=None)
    parser.add_argument("--raster_layer_blue_band", dest="raster_layer_blue_band", action="store",
                        type=json.loads, help="raster layer blue band dictionary: file path, "
                                              "layer index (int, starting 1), scale (float) "
                                              "and offset (float)", default=None)
    parser.add_argument("--raster_layer_green_band", dest="raster_layer_green_band", action="store",
                        type=json.loads, help="raster layer green band dictionary: file path, "
                                              "layer index (int, starting 1), scale (float) "
                                              "and offset (float)", default=None)
    parser.add_argument("--raster_layer_red_band", dest="raster_layer_red_band", action="store",
                        type=json.loads, help="raster layer red band dictionary: file path, "
                                              "layer index (int, starting 1), scale (float) "
                                              "and offset (float)", default=None)
    parser.add_argument("--raster_layer_nir_band", dest="raster_layer_nir_band", action="store",
                        type=json.loads, help="raster layer nir band dictionary: file path, "
                                              "layer index (int, starting 1), scale (float) "
                                              "and offset (float)", default=None)
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
    parser.add_argument("--output_plant_healthy_suffix", dest="output_plant_healthy_suffix", action="store", type=str,
                        help="Output field name suffix for plant healthy, maximum of three characters for "
                             "output shapefile", default=None)
    parser.add_argument("--output_plant_ndvi_suffix", dest="output_plant_ndvi_suffix", action="store", type=str,
                      help="Output field name suffix for plant ndvi, maximum of three characters for "
                           "output shapefile", default=None)
    parser.add_argument("--string_to_publish_number_of_steps", dest="string_to_publish_number_of_steps",
                        action="store", type=str, help="String to publish the number of steps", default=None)
    parser.add_argument("--string_to_publish_completed_steps_percentage",
                        dest="string_to_publish_completed_steps_percentage", action="store", type=str,
                        help="String to publish the completed steps percentage", default=None)
    args = parser.parse_args()
    if not args.crops_minimum_height:
        parser.print_help()
        return
    crops_minimum_height = args.crops_minimum_height
    if not args.crops_minimum_ndvi:
        parser.print_help()
        return
    crops_minimum_ndvi = args.crops_minimum_ndvi
    if not args.shadows_maximum_reflectance:
        parser.print_help()
        return
    shadows_maximum_reflectance = args.shadows_maximum_reflectance
    if not args.segmentation_method:
        parser.print_help()
        return
    if not args.output_plant_healthy_suffix:
        parser.print_help()
        return
    output_plant_healthy_suffix = args.output_plant_healthy_suffix
    output_plant_ndvi_suffix = None
    if args.output_plant_ndvi_suffix:
        output_plant_ndvi_suffix = args.output_plant_ndvi_suffix
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
        percentile_minimum_threshold = args.percentile_minimum_threshold
        if percentile_minimum_threshold < 0 or percentile_minimum_threshold > 1:
            sys.stderr.write("Error:\nInvalid value for percentile maximum threshold: {}".
                  format(str(percentile_minimum_threshold)))
            sys.stderr.flush()
            return
    if kmeans_clusters < 0 and percentile_minimum_threshold < 0:
        sys.stderr.write("Error:\nMethod segmentation must be: kmeans or percentile")
        sys.stderr.flush()
        return
    raster_layer_dsm_file_path = ''
    raster_layer_dsm_layer_index = -1
    raster_layer_dsm_layer_scale = 1.
    raster_layer_dsm_layer_offset = 0.
    raster_layer_dtm_file_path = ''
    raster_layer_dtm_layer_index = -1
    raster_layer_dtm_layer_scale = 1.
    raster_layer_dtm_layer_offset = 0.
    if crops_minimum_height > 0.:
        if not args.raster_layer_dsm_band:
            parser.print_help()
            return
        str_raster_layer_dsm_band = args.raster_layer_dsm_band
        if not 'file_path' in str_raster_layer_dsm_band:
            sys.stderr.write("Error:\nNo file path in raster layer dsm argument")
            sys.stderr.flush()
            return
        raster_layer_dsm_file_path = str_raster_layer_dsm_band['file_path']
        if not os.path.isfile(raster_layer_dsm_file_path):
            sys.stderr.write("Error:\nFile path in raster layer dsm argument is not a file")
            sys.stderr.flush()
            return
        if not os.path.exists(raster_layer_dsm_file_path):
            sys.stderr.write("Error:\nFile path in raster layer dsm argument not exists")
            sys.stderr.flush()
            return
        if not 'layer_index' in str_raster_layer_dsm_band:
            sys.stderr.write("Error:\nNo raster index in raster layer dsm argument")
            sys.stderr.flush()
            return
        raster_layer_dsm_layer_index = str_raster_layer_dsm_band['layer_index']
        if not isinstance(raster_layer_dsm_layer_index, int):
            sys.stderr.write("Error:\nRaster index in raster layer dsm argument is not an integer")
            sys.stderr.flush()
            return
        if raster_layer_dsm_layer_index < 1:
            sys.stderr.write("Error:\nRaster index in raster layer dsm argument is not a valid integer")
            sys.stderr.flush()
            return
        if not 'scale' in str_raster_layer_dsm_band:
            sys.stderr.write("Error:\nNo scale in raster layer dsm argument")
            sys.stderr.flush()
            return
        raster_layer_dsm_layer_scale = str_raster_layer_dsm_band['scale']
        if not isinstance(raster_layer_dsm_layer_scale, float):
            sys.stderr.write("Error:\nScale in raster layer dsm argument is not a float")
            sys.stderr.flush()
            return
        if raster_layer_dsm_layer_scale < 0:
            sys.stderr.write("Error:\nScale in raster layer dsm argument is negative")
            sys.stderr.flush()
            return
        if not 'offset' in str_raster_layer_dsm_band:
            sys.stderr.write("Error:\nNo offset in raster layer dsm argument")
            sys.stderr.flush()
            return
        raster_layer_dsm_layer_offset = str_raster_layer_dsm_band['offset']
        if not isinstance(raster_layer_dsm_layer_offset, float):
            sys.stderr.write("Error:\nOffset in raster layer argument is not a float")
            sys.stderr.flush()
            return
        str_raster_layer_dtm_band = args.raster_layer_dtm_band
        # raster_layer = {}
        if not 'file_path' in str_raster_layer_dtm_band:
            sys.stderr.write("Error:\nNo file path in raster layer dtm argument")
            sys.stderr.flush()
            return
        if not args.raster_layer_dtm_band:
            parser.print_help()
            return
        raster_layer_dtm_file_path = str_raster_layer_dtm_band['file_path']
        if not os.path.isfile(raster_layer_dtm_file_path):
            sys.stderr.write("Error:\nFile path in raster layer dtm argument is not a file")
            sys.stderr.flush()
            return
        if not os.path.exists(raster_layer_dtm_file_path):
            sys.stderr.write("Error:\nFile path in raster layer dtm argument not exists")
            sys.stderr.flush()
            return
        if not 'layer_index' in str_raster_layer_dtm_band:
            sys.stderr.write("Error:\nNo raster index in raster layer dtm argument")
            sys.stderr.flush()
            return
        raster_layer_dtm_layer_index = str_raster_layer_dtm_band['layer_index']
        if not isinstance(raster_layer_dtm_layer_index, int):
            sys.stderr.write("Error:\nRaster index in raster layer dtm argument is not an integer")
            sys.stderr.flush()
            return
        if raster_layer_dtm_layer_index < 1:
            sys.stderr.write("Error:\nRaster index in raster layer dtm argument is not a valid integer")
            sys.stderr.flush()
            return
        if not 'scale' in str_raster_layer_dtm_band:
            sys.stderr.write("Error:\nNo scale in raster layer dtm argument")
            sys.stderr.flush()
            return
        raster_layer_dtm_layer_scale = str_raster_layer_dtm_band['scale']
        if not isinstance(raster_layer_dtm_layer_scale, float):
            sys.stderr.write("Error:\nScale in raster layer dtm argument is not a float")
            sys.stderr.flush()
            return
        if raster_layer_dtm_layer_scale < 0:
            sys.stderr.write("Error:\nScale in raster layer dtm argument is negative")
            sys.stderr.flush()
            return
        if not 'offset' in str_raster_layer_dtm_band:
            sys.stderr.write("Error:\nNo offset in raster layer dtm argument")
            sys.stderr.flush()
            return
        raster_layer_dtm_layer_offset = str_raster_layer_dtm_band['offset']
        if not isinstance(raster_layer_dtm_layer_offset, float):
            sys.stderr.write("Error:\nOffset in raster layer argument is not a float")
            sys.stderr.flush()
            return
    if not args.raster_layer_blue_band:
        parser.print_help()
        return
    str_raster_layer_blue_band = args.raster_layer_blue_band
    # raster_layer = {}
    if not 'file_path' in str_raster_layer_blue_band:
        sys.stderr.write("Error:\nNo file path in raster layer blue band argument")
        sys.stderr.flush()
        return
    raster_layer_blue_band_file_path = str_raster_layer_blue_band['file_path']
    if not os.path.isfile(raster_layer_blue_band_file_path):
        sys.stderr.write("Error:\nFile path in raster layer blue band argument is not a file")
        sys.stderr.flush()
        return
    if not os.path.exists(raster_layer_blue_band_file_path):
        sys.stderr.write("Error:\nFile path in raster layer blue band argument not exists")
        sys.stderr.flush()
        return
    if not 'layer_index' in str_raster_layer_blue_band:
        sys.stderr.write("Error:\nNo raster index in raster layer blue band argument")
        sys.stderr.flush()
        return
    raster_layer_blue_band_layer_index = str_raster_layer_blue_band['layer_index']
    if not isinstance(raster_layer_blue_band_layer_index, int):
        sys.stderr.write("Error:\nRaster index in raster layer blue band argument is not an integer")
        sys.stderr.flush()
        return
    if raster_layer_blue_band_layer_index < 1:
        sys.stderr.write("Error:\nRaster index in raster layer blue band argument is not a valid integer")
        sys.stderr.flush()
        return
    if not 'scale' in str_raster_layer_blue_band:
        sys.stderr.write("Error:\nNo scale in raster layer blue band argument")
        sys.stderr.flush()
        return
    raster_layer_blue_band_layer_scale = str_raster_layer_blue_band['scale']
    if not isinstance(raster_layer_blue_band_layer_scale, float):
        sys.stderr.write("Error:\nScale in raster layer blue band argument is not a float")
        sys.stderr.flush()
        return
    if raster_layer_blue_band_layer_scale < 0:
        sys.stderr.write("Error:\nScale in raster layer blue band argument is negative")
        sys.stderr.flush()
        return
    if not 'offset' in str_raster_layer_blue_band:
        sys.stderr.write("Error:\nNo offset in raster layer blue band argument")
        sys.stderr.flush()
        return
    raster_layer_blue_band_layer_offset = str_raster_layer_blue_band['offset']
    if not isinstance(raster_layer_blue_band_layer_offset, float):
        sys.stderr.write("Error:\nOffset in raster layer argument is not a float")
        sys.stderr.flush()
        return
    if not args.raster_layer_green_band:
        parser.print_help()
        return
    str_raster_layer_green_band = args.raster_layer_green_band
    # raster_layer = {}
    if not 'file_path' in str_raster_layer_green_band:
        sys.stderr.write("Error:\nNo file path in raster layer green band argument")
        sys.stderr.flush()
        return
    raster_layer_green_band_file_path = str_raster_layer_green_band['file_path']
    if not os.path.isfile(raster_layer_green_band_file_path):
        sys.stderr.write("Error:\nFile path in raster layer green band argument is not a file")
        sys.stderr.flush()
        return
    if not os.path.exists(raster_layer_green_band_file_path):
        sys.stderr.write("Error:\nFile path in raster layer green band argument not exists")
        sys.stderr.flush()
        return
    if not 'layer_index' in str_raster_layer_green_band:
        sys.stderr.write("Error:\nNo raster index in raster layer green band argument")
        sys.stderr.flush()
        return
    raster_layer_green_band_layer_index = str_raster_layer_green_band['layer_index']
    if not isinstance(raster_layer_green_band_layer_index, int):
        sys.stderr.write("Error:\nRaster index in raster layer green band argument is not an integer")
        sys.stderr.flush()
        return
    if raster_layer_green_band_layer_index < 1:
        sys.stderr.write("Error:\nRaster index in raster layer green band argument is not a valid integer")
        sys.stderr.flush()
        return
    if not 'scale' in str_raster_layer_green_band:
        sys.stderr.write("Error:\nNo scale in raster layer green band argument")
        sys.stderr.flush()
        return
    raster_layer_green_band_layer_scale = str_raster_layer_green_band['scale']
    if not isinstance(raster_layer_green_band_layer_scale, float):
        sys.stderr.write("Error:\nScale in raster layer green band argument is not a float")
        sys.stderr.flush()
        return
    if raster_layer_green_band_layer_scale < 0:
        sys.stderr.write("Error:\nScale in raster layer green band argument is negative")
        sys.stderr.flush()
        return
    if not 'offset' in str_raster_layer_green_band:
        sys.stderr.write("Error:\nNo offset in raster layer green band argument")
        sys.stderr.flush()
        return
    raster_layer_green_band_layer_offset = str_raster_layer_green_band['offset']
    if not isinstance(raster_layer_green_band_layer_offset, float):
        sys.stderr.write("Error:\nOffset in raster layer argument is not a float")
        sys.stderr.flush()
        return
    if not args.raster_layer_red_band:
        parser.print_help()
        return
    str_raster_layer_red_band = args.raster_layer_red_band
    # raster_layer = {}
    if not 'file_path' in str_raster_layer_red_band:
        sys.stderr.write("Error:\nNo file path in raster layer red band argument")
        sys.stderr.flush()
        return
    raster_layer_red_band_file_path = str_raster_layer_red_band['file_path']
    if not os.path.isfile(raster_layer_red_band_file_path):
        sys.stderr.write("Error:\nFile path in raster layer red band argument is not a file")
        sys.stderr.flush()
        return
    if not os.path.exists(raster_layer_red_band_file_path):
        sys.stderr.write("Error:\nFile path in raster layer red band argument not exists")
        sys.stderr.flush()
        return
    if not 'layer_index' in str_raster_layer_red_band:
        sys.stderr.write("Error:\nNo raster index in raster layer red band argument")
        sys.stderr.flush()
        return
    raster_layer_red_band_layer_index = str_raster_layer_red_band['layer_index']
    if not isinstance(raster_layer_red_band_layer_index, int):
        sys.stderr.write("Error:\nRaster index in raster layer red band argument is not an integer")
        sys.stderr.flush()
        return
    if raster_layer_red_band_layer_index < 1:
        sys.stderr.write("Error:\nRaster index in raster layer red band argument is not a valid integer")
        sys.stderr.flush()
        return
    if not 'scale' in str_raster_layer_red_band:
        sys.stderr.write("Error:\nNo scale in raster layer red band argument")
        sys.stderr.flush()
        return
    raster_layer_red_band_layer_scale = str_raster_layer_red_band['scale']
    if not isinstance(raster_layer_red_band_layer_scale, float):
        sys.stderr.write("Error:\nScale in raster layer red band argument is not a float")
        sys.stderr.flush()
        return
    if raster_layer_red_band_layer_scale < 0:
        sys.stderr.write("Error:\nScale in raster layer red band argument is negative")
        sys.stderr.flush()
        return
    if not 'offset' in str_raster_layer_red_band:
        sys.stderr.write("Error:\nNo offset in raster layer red band argument")
        sys.stderr.flush()
        return
    raster_layer_red_band_layer_offset = str_raster_layer_red_band['offset']
    if not isinstance(raster_layer_red_band_layer_offset, float):
        sys.stderr.write("Error:\nOffset in raster layer argument is not a float")
        sys.stderr.flush()
        return
    if not args.raster_layer_nir_band:
        parser.print_help()
        return
    str_raster_layer_nir_band = args.raster_layer_nir_band
    # raster_layer = {}
    if not 'file_path' in str_raster_layer_nir_band:
        sys.stderr.write("Error:\nNo file path in raster layer nir band argument")
        sys.stderr.flush()
        return
    raster_layer_nir_band_file_path = str_raster_layer_nir_band['file_path']
    if not os.path.isfile(raster_layer_nir_band_file_path):
        sys.stderr.write("Error:\nFile path in raster layer nir band argument is not a file")
        sys.stderr.flush()
        return
    if not os.path.exists(raster_layer_nir_band_file_path):
        sys.stderr.write("Error:\nFile path in raster layer nir band argument not exists")
        sys.stderr.flush()
        return
    if not 'layer_index' in str_raster_layer_nir_band:
        sys.stderr.write("Error:\nNo raster index in raster layer nir band argument")
        sys.stderr.flush()
        return
    raster_layer_nir_band_layer_index = str_raster_layer_nir_band['layer_index']
    if not isinstance(raster_layer_nir_band_layer_index, int):
        sys.stderr.write("Error:\nRaster index in raster layer nir band argument is not an integer")
        sys.stderr.flush()
        return
    if raster_layer_nir_band_layer_index < 1:
        sys.stderr.write("Error:\nRaster index in raster layer nir band argument is not a valid integer")
        sys.stderr.flush()
        return
    if not 'scale' in str_raster_layer_nir_band:
        sys.stderr.write("Error:\nNo scale in raster layer nir band argument")
        sys.stderr.flush()
        return
    raster_layer_nir_band_layer_scale = str_raster_layer_nir_band['scale']
    if not isinstance(raster_layer_nir_band_layer_scale, float):
        sys.stderr.write("Error:\nScale in raster layer nir band argument is not a float")
        sys.stderr.flush()
        return
    if raster_layer_nir_band_layer_scale < 0:
        sys.stderr.write("Error:\nScale in raster layer nir band argument is negative")
        sys.stderr.flush()
        return
    if not 'offset' in str_raster_layer_nir_band:
        sys.stderr.write("Error:\nNo offset in raster layer nir band argument")
        sys.stderr.flush()
        return
    raster_layer_nir_band_layer_offset = str_raster_layer_nir_band['offset']
    if not isinstance(raster_layer_nir_band_layer_offset, float):
        sys.stderr.write("Error:\nOffset in raster layer argument is not a float")
        sys.stderr.flush()
        return
    if (raster_layer_blue_band_file_path.casefold() != raster_layer_green_band_file_path.casefold()
            or raster_layer_blue_band_file_path.casefold() != raster_layer_red_band_file_path.casefold()
            or raster_layer_blue_band_file_path.casefold() != raster_layer_nir_band_file_path.casefold()):
        sys.stderr.write("Error:\nRaster file must be the same for all bands")
        sys.stderr.flush()
        return
    if (raster_layer_blue_band_layer_index == raster_layer_green_band_layer_index
        or raster_layer_blue_band_layer_index == raster_layer_red_band_layer_index
            or raster_layer_blue_band_layer_index == raster_layer_nir_band_layer_index):
        sys.stderr.write("Error:\nRaster index must be different for all bands")
        sys.stderr.flush()
        return
    raster_layer_file_path = raster_layer_blue_band_file_path
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
    str_error = process(crops_minimum_height,
                        crops_minimum_ndvi,
                        shadows_maximum_reflectance,
                        segmentation_method,
                        kmeans_clusters,
                        output_plant_healthy_suffix,
                        output_plant_ndvi_suffix,
                        percentile_maximum_threshold,
                        raster_layer_dsm_file_path,
                        raster_layer_dsm_layer_index,
                        raster_layer_dsm_layer_scale,
                        raster_layer_dsm_layer_offset,
                        raster_layer_dtm_file_path,
                        raster_layer_dtm_layer_index,
                        raster_layer_dtm_layer_scale,
                        raster_layer_dtm_layer_offset,
                        raster_layer_file_path,
                        raster_layer_blue_band_layer_index,
                        raster_layer_blue_band_layer_scale,
                        raster_layer_blue_band_layer_offset,
                        raster_layer_green_band_layer_index,
                        raster_layer_green_band_layer_scale,
                        raster_layer_green_band_layer_offset,
                        raster_layer_red_band_layer_index,
                        raster_layer_red_band_layer_scale,
                        raster_layer_red_band_layer_offset,
                        raster_layer_nir_band_layer_index,
                        raster_layer_nir_band_layer_scale,
                        raster_layer_nir_band_layer_offset,
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
