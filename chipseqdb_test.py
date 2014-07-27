#
# A test harness for chipseqdb.py
#

from read_config import *
from chipseqdb import *
from chipseqdb_plots import *

from argParser import ArgParser
ap = ArgParser(sys.argv)

def splash():
    print "==================================="
    print ". Project Guacamole"
    print ". . . by Victor Hanson-Smith"
    print ". . . victorhansonsmith@gmail.com"
    print "==================================="
#
# Build, or add to, the database
#
def import_data(con):
    for sp in ap.params["species"]:
        print "\n. Importing data for species", sp
        speciesname = ap.params["species"][sp]["name"]
        con = import_species(speciesname, con)
        speciesid = get_species_id(speciesname, con)
                
        gffpath = ap.params["species"][sp]["gff"]
        con = import_gff(gffpath, speciesid, con)
        
        ii = -1
        for groupname in ap.params["species"][sp]["rgroups"]:
            print "\n. Importing group", groupname
            con = add_repgroup(groupname, con)
            rgroupid = get_repgroup_id(groupname, con)
                        
            for jj in ap.params["species"][sp]["rgroups"][groupname]["reps"]:
                print "37:", sp, speciesname, speciesid, groupname, rgroupid, jj
                ii += 1
                
                summitpath = ap.params["species"][sp]["rgroups"][groupname]["reps"][jj]
                repname = groupname + "-" + jj.__str__()
                con = add_replicate(repname, speciesid, con)
                repid = get_repid(repname, speciesid, con)
                con = add_rep2group(repid, rgroupid, con)
                con = import_summits(summitpath, repid, con)
                con = map_summits2genes(con, repid, speciesid=speciesid)
    return con

def correlate_replicates(con ):
    rgroups = get_repgroup_ids(con)
    for rg in rgroups:
        rgroupid = rg[0]
        repids = get_reps_in_group(rgroupid, con)
        for ii in range(0, repids.__len__()):
            for jj in range(1, repids.__len__()):
                if ii != jj:
                    #print repids[ii][0], repids[jj][0]   
                    correlate_two_reps(repids[ii][0], repids[jj][0], con)

######################################################################
#
# main
#
splash()

"""If the user gives a configpath, then it's referenced
data will be imported into the database."""
configpath = ap.getOptionalArg("--configpath")
if configpath != False:
    ap.params = read_config( configpath )
"""If the user didn't give a configpath, then we at
least need a dbpath (to load a prior database)."""
dbpath = ap.getOptionalArg("--dbpath")
if configpath == False and dbpath == False:
    print "\n. Error, you need to specify either:"
    print "1. a configuration path, using --configpath, that describes data that will be imported into the DB."
    print "2. an existing database, using --dbpath, whose contents will be read and imported."
    print ""
    exit()
con = build_db(dbpath=dbpath)
if configpath != False:
    con = import_data(con)

"""Compare all pairs of replicates."""
correlate_replicates(con)
