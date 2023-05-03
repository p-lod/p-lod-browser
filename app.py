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
# cache.init_app(app)

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

def p_lod_html_head(r, html_dom):
    html_dom.head += meta(charset="utf-8")
    html_dom.head += meta(http_equiv="X-UA-Compatible", content="IE=edge")
    html_dom.head += meta(name="viewport", content="width=device-width, initial-scale=1")    
    html_dom.head += link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css", integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2", crossorigin="anonymous")
    html_dom.head += script(src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js", integrity="sha512-894YE6QWD5I59HgZOGReFYm4dnWc1Qt5NtvYSaNcOP+u1T9qYdvdihz0PPSiiqn/+/3e7Jo4EaG7TubfWGUrMQ==", crossorigin="anonymous", referrerpolicy="no-referrer")
    html_dom.head += script(src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/galleria.min.js", integrity="sha512-vRKUU1GOjCKOTRhNuhQelz4gmhy6NPpB8N41c7a36Cxl5QqKeB9VowP8S7x8Lf3B8vZVURBxGlPpvyiRHh+CKg==",crossorigin="anonymous",referrerpolicy="no-referrer")
    html_dom.head += script(src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/js/bootstrap.bundle.min.js",integrity="sha384-ho+j7jyWK8fNQe+A12Hb8AhRq26LrZ/JpcUGGOn+Y7RsweNrtN/tE3MoK7ZeZDyx",crossorigin="anonymous")
    html_dom.head += link(rel="stylesheet", href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css", integrity="sha512-xodZBNTC5n17Xt2atTPuE1HxjVMSvLVW9ocqUKLsCC5CXdbqCmblAshOMAS6/keqq/sMZMZ19scR4PsZChSR7A==", crossorigin="")
    html_dom.head += script(src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js", integrity="sha512-XQoYMqMTK8LvdxXYG3nZ448hOEQiglfqkJs1NOQV44cWnUrBc8PkAOcXy20w0vlaXaVUearIOBhiXZ5V3ynxwA==", crossorigin="")
    html_dom.head += link(rel="stylesheet", href="/static/css/sticky-footer-navbar.css")
    html_dom.head += meta(name="DC.title",lang="en",content=r.identifier )
    html_dom.head += meta(name="DC.identifier", content=f"urn:p-lod:id:{r.identifier}" )



def p_lod_page_navbar(r, html_dom):
    with html_dom:
      # feature request: suppress a link when displaying the page it links to.
      with header():
        with nav(cls="navbar navbar-expand-md navbar-dark fixed-top bg-dark"):
          img(src="/static/images/under-construction.png", style="width:35px")
          span(raw("&nbsp;"))
          a("PALP", href="/start", cls="navbar-brand")
          if r.label:
           span(r.label, cls="navbar-brand")
          elif r.identifier:
           if r.rdf_type is not None:
            span(f"{r.rdf_type} ", cls="navbar-brand")
           span(r.identifier, cls="navbar-brand")
          else:
           span("", cls="navbar-brand")

          if r.broader:
            with span(cls="navbar-brand"):
              span("(")
              a(r.broader.replace("urn:p-lod:id:",""), href=f"/browse/{r.broader.replace('urn:p-lod:id:','')}")
              span(")")

          p_in_p = json.loads(r.get_predicate_values('urn:p-lod:id:p-in-p-url'))
          if p_in_p:
            with span(cls="navbar-brand"):
              span(" [")
              a("Pompeii in Pictures", href= p_in_p[0])
              span("]")

          wiki_en = json.loads(r.get_predicate_values('urn:p-lod:id:wiki-en-url'))
          if wiki_en:
            with span(cls="navbar-brand"):
              span(" [")
              a("Wiki (en)", href= wiki_en[0])
              span("]")

          wiki_it = json.loads(r.get_predicate_values('urn:p-lod:id:wiki-it-url'))
          if wiki_it:
            with span(cls="navbar-brand"):
              span(" [")
              a("Wiki (it)", href= wiki_it[0])
              span("]")

          wikidata = json.loads(r.get_predicate_values('urn:p-lod:id:wikidata-url'))
          if wikidata:
            with span(cls="navbar-brand"):
              span(" [")
              a("Wikidata", href= wikidata[0])
              span("]")

          pleiades = json.loads(r.get_predicate_values('urn:p-lod:id:pleiades-url'))
          if pleiades:
            with span(cls="navbar-brand"):
              span(" [")
              a("Pleiades", href= pleiades[0])
              span("]")

          with form(cls="navbar-form navbar-right", role="search", action="/full-text-search"):
                        with span(cls="form-group"):
                            input_(id="q", name="q", type="text",cls="form-control",placeholder="Keyword Search...")

def p_lod_page_footer(r, doc):
    with doc:
      with footer(cls="footer"):
        with span():
          small("Pompeii Linked Open Data (P-LOD) is jointly overseen by Sebastian Heath (NYU) and Eric Poehler (UMass-Amherst).")

# convenience functions
def urn_to_anchor(urn):

  label         = urn.replace("urn:p-lod:id:","") # eventually get the actual label
  relative_url  = f'/browse/{urn.replace("urn:p-lod:id:","")}'

  return relative_url, label



def img_src_from_luna_info(l_collection_id, l_record, l_media):

  img_src = None #default if no URLs present (probably means LUNA doesn't have image though triplestore thinks it does)
  img_description = None

  luna_json = json.loads(urlopen(f'https://umassamherst.lunaimaging.com/luna/servlet/as/fetchMediaSearch?mid={l_collection_id}~{l_record}~{l_media}&fullData=true').read())

  if len(luna_json):

    img_attributes = json.loads(luna_json[0]['attributes'])

    if 'image_description_english' in img_attributes.keys():
      img_description = img_attributes['image_description_english']
    else:
      try:
        if l_collection_id == 'umass~14~14':
          img_description = json.loads(luna_json[0]['fieldValues'])[2]['value']
        elif l_collection_id == 'umass~16~16':
          img_description = json.loads(luna_json[0]['fieldValues'])[1]['value']
        else:
          img_description = f"unrecognized collection {l_collection_id}"
      except:
        img_description = "Trying to get description failed"

    if 'urlSize4' in img_attributes.keys(): # use size 4, sure, but only if there's nothing else
      img_src = img_attributes['urlSize4']
    if 'urlSize2' in img_attributes.keys(): # preferred
      img_src = img_attributes['urlSize2']
    elif 'urlSize3' in img_attributes.keys():
      img_src = img_attributes['urlSize3']
    else:
      img_src = img_attributes['urlSize1']

  return img_src, img_description

def adjust_geojson(geojson_str, rdf_type = None): # working on shifting geojson .00003 to the N  

  # offsets

  xoff = 0
  yoff =  0
  if rdf_type == "region":
    yoff = 0 

  # xoff = -0.0000075
  # yoff =  0.000037
  # if rdf_type == "region":
  #   yoff = .00072

  g = json.loads(geojson_str)
  if g['type'] == 'FeatureCollection':
    for f in g['features']:
      s =  shape(f['geometry'])
      f['geometry'] = mapping(translate(s, xoff=xoff, yoff=yoff, zoff=0.0))
    return json.dumps(g)

  elif g['type'] == 'Feature':
    s =  shape(g['geometry'])
    g['geometry'] = mapping(translate(s, xoff=xoff, yoff=yoff, zoff=0.0))
    return json.dumps(g)
  else:
    return geojson_str


def p_lod_html_document(r = POMPEII,renderer = None):

  html_dom = dominate.document(title=f"Pompeii Artistic Landscape Project: {r.identifier}" )

  palp_html_head(r, html_dom)
  html_dom.body
  palp_page_navbar(r,html_dom)

  if r:
    renderer(r, html_dom)

  palp_page_footer(r, html_dom)

  return html_dom

# The PALP Verbs that Enable Navigation

@app.route('/')
def index():
  return """
  <html>
  <head>
  <title>Pompeii Linked Open Data (P-LOD)</title>
  </head>
  <body>
  <h1>Pompeii Linked Open Data (P-LOD)</h1>
  <h2>Browse URNs</h2>
  <ul>
  <li><a href="/urn/urn:p-lod:id:pompeii">http://p-lod.org/urn/urn:p-lod:id:pompeii</a> (Replace with any P-LOD URN.)</li>
  <li><a href="/urn/urn:p-lod:id:ariadne">http://p-lod.org/urn/urn:p-lod:id:ariadne</a></li>
  <li><a href="/urn/urn:p-lod:id:snake">http://p-lod.org/urn/urn:p-lod:id:snake</a></li>
  </ul>
  <h2>API</h2>
  <ul>
  <li>/api/geojson
  <ul>
  <li><a href="/api/geojson/pompeii">http://p-lod.org/api/geojson/pompeii</a> (Replace with any P-LOD identifier.)</li>
  <li><a href="/api/geojson/snake">http://p-lod.org/api/geojson/snake</a></li>
  </ul>
  </li>
  <li>/api/spatial_children
  <ul>
  <li><a href="/api/spatial_children/r1">http://p-lod.org/api/spatial_children/r1</a></li>
  </ul>
  </li>
  </ul>
  <footer>The P-LOD initiative is jointly directed by <a href="https://isaw.nyu.edu/people/faculty/isaw-faculty/sebastian-heath">Sebastian Heath</a> (NYU) and <a href="https://www.umass.edu/classics/member/eric-poehler">Eric Poehler</a> (UMass Amherst). It includes data collected for the Getty funded <a href="http://palp.art">Pompeii Artistic Landscape Project</a>.</footer>
  </body>
  </html>"""

# /urn
@app.route('/urn/<path:urn>')
def web_api_urn(urn):
  html_df = plodlib.PLODResource(urn.replace('urn:p-lod:id:',''))._id_df

  html_df = html_df.replace(r"^(urn:p-lod:id:.*)",r'<a href="/urn/\1">\1</a>', regex=True)
  html_df = html_df.replace(r"^(http(s|)://.*)",r'<a href="\1" target="_new">\1</a>', regex=True)

  return html_df.to_html(escape = False, header = False)

# /api handlers
@app.route('/api/geojson/<path:identifier>')
def web_api_geojson(identifier):
  return Response(plodlib.PLODResource(identifier).geojson, mimetype='application/json')

@app.route('/api/images/<path:identifier>')
def web_api_images(identifier):
  return Response(plodlib.PLODResource(identifier).gather_images(), mimetype='application/json')

@app.route('/api/spatial_children/<path:identifier>')
def web_api_spatial_childern(identifier):
  return Response(plodlib.PLODResource(identifier).spatial_children(), mimetype='application/json')