# Radian-Web

RADIAN is a Python-based tool for generating synthetic spatial datasets [https://doi.org/10.1080/15230406.2024.2377981] 

RADIAN-Web is a web-based tool which implements (and improves!) all the existing functionalities of RADIAN, as well as enhancing it's usability and efficiency. 

![Screentshot of Radian-Web](RadianWeb.png)

## What does RADIAN do?
* RADIAN generates synthetic spatial datasets, produced using a 2-D Gassian distribution to simulate spatial feature coordinates, given a polygon boundary that may define a country, city, or other arbitrary administrative boundary.
* It utilizes a two stage generation process, with the primary stage taking place at the level of the whole boundary polygon, and the secondary stage taking place locally within randomly generated Voronoi polygons, within said boundary region.
* Common metadata attributes are generated, including:
  * Random strings (given by Regex), integers and timestamps
  * Custom attributes with values and weights specified via a .CSV
* It can export data in .GeoJSON format as well as PostgreSQL ready .SQL files.

## How does RADIAN-Web differ from ordinary RADIAN?
The obvious difference is of course that RADIAN-web operates within the users browser, without any need to install any software or dependencies on a local machine. 
Given one of the primary use cases for RADIAN being in educational and classroom settings, RADIAN-web provides a great leap in usability of the software as now it can be distributed to students (or educators) simply by visiting the link via a browser.
