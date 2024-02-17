import html

# https://getbootstrap.com/docs/4.0/examples/sticky-footer-navbar/ is the theme this uses.

# because dominate will stomp on html
py_html = html

import json
# import os
# import re
# import sys

from urllib.request import urlopen

import pandas as pd

import dominate
from dominate.tags import *
from dominate.util import raw

# from bs4 import BeautifulSoup

from flask import Flask, json, request, redirect, Response
# Response
from flask_caching import Cache

import rdflib as rdf
from rdflib.plugins.stores.sparqlstore import SPARQLStore

from shapely.geometry import shape, mapping
from shapely.affinity import translate

from string import Template

import traceback

import plodlib

ns = {"dcterms" : "http://purl.org/dc/terms/",
      "owl"     : "http://www.w3.org/2002/07/owl#",
      "rdf"     : "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
      "rdfs"    : "http://www.w3.org/2000/01/rdf-schema#" ,
      "p-lod"   : "urn:p-lod:id:" }


cache = Cache(config={
  'CACHE_TYPE': 'FileSystemCache',
  'CACHE_DIR': 'cache',
  'CACHE_DEFAULT_TIMEOUT': 0,
  'CACHE_IGNORE_ERRORS': True,
  'CACHE_THRESHOLD': 1000
  })
app = Flask(__name__)
cache.init_app(app)

# Connect to the remote triplestore with read-only connection
store = SPARQLStore(endpoint="http://p-lod.org:3030/plod_endpoint/query",
                                                       context_aware = False,
                                                       returnFormat = 'json')
g = rdf.Graph(store)

# GLOBALS
POMPEII = plodlib.PLODResource('pompeii') # useful to have it conveniently available
browse_concept_icon = '⬀'
browse_within_icon = '⧉'
browse_image_icon = '🔎'



# The PALP Verbs that Enable Navigation

@app.route('/')
def index():
  with open('static/templates/start_template.html', encoding="utf-8") as f:
      start_template_txt = f.read()
      
  return start_template_txt

# helper function
def embed_image(row):
  print(row)
  print(type(row))
  best_image_urn = row
  best_image_r = plodlib.PLODResource(best_image_urn.replace('urn:p-lod:id:',''))
  best_image_thumbnail_url = json.loads(best_image_r.get_predicate_values('urn:p-lod:id:x-luna-url-1'))[0]
  image_html = f'<a href="urn/{best_image_urn}">{best_image_urn}</a><br><img src="{best_image_thumbnail_url}">'
  print(image_html)
  return image_html


# /urn
@app.route('/urn/<path:urn>')
def web_api_urn(urn):

  r = plodlib.PLODResource(urn.replace('urn:p-lod:id:',''))

  identifier_df = r._id_df.sort_values(by = 'p').copy()

  if 'urn:p-lod:id:geojson' in identifier_df.index:
    identifier_df.loc['urn:p-lod:id:geojson','o'] = f'[<a href="/api/geojson/{r.identifier}">view as json</a>] [<a target="_new" href="http://geojson.io/#data=data:text/x-url,http%3A%2F%2Fp-lod.org%2Fapi%2Fgeojson%2F{r.identifier}">view as map at geojson.io</a>]'
    identifier_df.rename(index={'urn:p-lod:id:geojson':'geojson'},inplace=True)

  try:
      mask = identifier_df.index == 'urn:p-lod:id:best-image'
      identifier_df.loc[mask, 'o'] = identifier_df.loc[mask, 'o'].apply(embed_image)

  except Exception as e:
    print("Error: ", e)
    print(traceback.format_exc())

  try:
    if 'urn:p-lod:id:x-luna-url-2' in identifier_df.index:
      image_url = identifier_df.loc['urn:p-lod:id:x-luna-url-2','o']
      image__html = f'<a href="{image_url}">{image_url}</a><br><img src="{image_url}">'
      identifier_df.loc['urn:p-lod:id:x-luna-url-2','o'] = image__html
  except: pass

  identifier_df = identifier_df.replace(r"^(http(s|)://.*)",r'<a href="\1" target="_new">\1</a>', regex=True)
  identifier_df.reset_index(inplace=True, drop=False)
  identifier_df = identifier_df.replace(r"^(urn:p-lod:id:.*)",r'<a href="/urn/\1">\1</a>', regex=True)
  predicate_object_html =  identifier_df.to_html(escape = False, header = False, index=False, classes='table table-striped')

  subject_predicate_html = ""
  as_object_df = pd.DataFrame.from_dict(json.loads(r.as_object()))
  if len(as_object_df) > 0:
    as_object_df = as_object_df.replace(r"^(urn:p-lod:id:.*)",r'<a href="/urn/\1">\1</a>', regex=True)
    as_object_df['object'] = urn
    subject_predicate_html =  f'<h2 class="text-body-emphasis">Links to {urn}</h2><span>Max. 15,000 Shown</span>{as_object_df.to_html(escape = False, header = False, classes="table table-striped")}'

  subject_object_html = ""
  as_predicate_df = pd.DataFrame.from_dict(json.loads(r.as_predicate()))
  if len(as_predicate_df) > 0:
    as_predicate_df = as_predicate_df.replace(r"^(urn:p-lod:id:.*)",r'<a href="/urn/\1">\1</a>', regex=True)
    as_predicate_df = as_predicate_df.replace(r"^(http(s|)://.*)",r'<a href="\1" target="_new">\1</a>', regex=True)
    as_predicate_df['predicate'] = urn
    subject_object_html =  f'<h2 class="text-body-emphasis">{urn} creates links between</h2><span>Max. 15,000 Shown</span>{as_predicate_df[["subject","predicate","object"]].to_html(escape = False, header= False, classes="table table-striped")}'

  with open('static/templates/urn_template.html', encoding="utf-8") as f:
    urn_template_txt = f.read()
  urn_template = Template(urn_template_txt)

  return urn_template.substitute({'urn':urn,
                                  'identifier':r.identifier,
                                  'urn_type':r.rdf_type,
                                  'predicate_object_html': predicate_object_html,
                                  'subject_predicate_html': subject_predicate_html,
                                  'subject_object_html': subject_object_html,})

# /api handlers
@app.route('/api/depicted_where/<path:identifier>')
def web_api_depicted_where(identifier):
  return Response(plodlib.PLODResource(identifier).depicted_where(), mimetype='application/json')

@app.route('/api/depicts_concepts/<path:identifier>')
def web_api_depicts_concepts(identifier):
  return Response(plodlib.PLODResource(identifier).depicts_concepts(), mimetype='application/json')

@app.route('/api/geojson/<path:identifier>')
def web_api_geojson(identifier):
  return Response(plodlib.PLODResource(identifier).geojson, mimetype='application/json')

@app.route('/api/images/<path:identifier>')
def web_api_images(identifier):
  return Response(plodlib.PLODResource(identifier).gather_images(), mimetype='application/json')

@app.route('/api/spatial_ancestors/<path:identifier>')
def web_api_spatial_ancestors(identifier):
  return Response(plodlib.PLODResource(identifier).spatial_ancestors(), mimetype='application/json')

@app.route('/api/spatial_children/<path:identifier>')
def web_api_spatial_children(identifier):
  return Response(plodlib.PLODResource(identifier).spatial_children(), mimetype='application/json')

@app.route('/api/spatially_within/<path:identifier>')
def web_api_spatially_within(identifier):
  return Response(plodlib.PLODResource(identifier).spatially_within(), mimetype='application/json')

@app.route('/api/within_region/<path:identifier>')
def web_api_within_region(identifier):
  return Response(plodlib.PLODResource(identifier).within_region(), mimetype='application/json')
