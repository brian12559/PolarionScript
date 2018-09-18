import ConfigParser
import datetime
import os
import re
import user
import sys

import bugzilla

#this is just an issue within eclipse as this runs fine from terminal window
from pylarion.exceptions import PylarionLibException
from pylarion.hyperlink import Hyperlink
from pylarion.plan import Plan
from pylarion.text import Text
from pylarion.user import User
from pylarion.work_item import Requirement
from pylarion.work_item import _WorkItem
import time

BUGZILLA_SERVER = "https://bugzilla.redhat.com/xmlrpc.cgi"
BUGZILLA_PRODUCT= "Red Hat Cluster Suite"
BUGZILLA_PRODUCT= "test"
BUGZILLA_VERSION = "13.0 (Queens)"
POLARION_PRODUCT = "Polarion" #was openstack  this is going to have to be picked up from the Bugzilla ticket and then looked up

#conversion dictionaries, bugzilla:polarion
SEV_DICT = {"urgent": "must_have", "high": "must_have", "medium": "should_have", "low": "nice_to_have", "unspecified": "will_not_have"}
PRIOR_DICT = {"urgent": float(90.0), "high": float(70.0), "medium": float(50.0), "low": float(30.0), "unspecified": float(10.0)}
PROJ_DICT = {"test": "Polarion", "Red Hat Cluster Suite": "RHELOpenStackPlatform"}

class ConfigFileMissingException(Exception):
    pass

def parse_config():
    conf_file = os.path.join(user.home, ".pylarion")
    if not os.path.isfile(conf_file):
        raise ConfigFileMissingException

    config = ConfigParser.RawConfigParser()
    config.read(conf_file)
    params_dict = {}
    for params in config.items("webservice"):
        params_dict[params[0]] = params[1]

    return params_dict

def get_bug_params(bug):
    named_parms = dict()
    bug_summary = re.sub(r"[^\x00-\x7F]+", " ", bug.summary)
    priority = bug.priority
    severity = bug.severity
    product = bug.product
    bug_id = bug.id
    description = ""
    if bug.getcomments():
        comment = bug.getcomments()[0]
        # the description is always the first comment.
        description = comment["text"]

    dfg = bug.internal_whiteboard

    return bug_summary, product, named_parms, description, bug.weburl, bug_id, priority, severity, dfg

def isRequirementInPolarion(bug_id, bug_project):
    query_str = "SELECT tc.c_uri from WORKITEM tc join project proj on proj.c_uri=tc.fk_uri_project where proj.c_id='%s' and tc.c_title like ('BZ_id=%s%%') and tc.c_type = 'requirement'" % (bug_project, bug_id)
    for i in range(0, 10):  # WA for Polarion disconnection from time to time
        try:
            items = _WorkItem.query(query_str, is_sql=True, fields=["work_item_id", "title"])
            if len(items) > 0:
                for item in items:
                    tc = Requirement(uri=item.uri)
                    print "\n" + tc.work_item_id
                print "\nRequirement already in Polarion: " + str(bug_id)
                return True
            break
        except Exception as inst:
            print inst
            i += 1
            time.sleep(10)

    return False

def get_rfes_from_bugzilla(bugs):
    # Open connection into bugzilla
    user_params = parse_config()
    username = user_params.get("user") + "@redhat.com"
    password = user_params.get("password")
    
    #for for local testing
    username = "bmurray@redhat.com"
    password = "XXXXX"
    if bugs == "":
        bugs = "1011755,1003044"
    
    #connect to Bugzilla    
    bz_connection = bugzilla.RHBugzilla(url=BUGZILLA_SERVER)
    bz_connection.login(username,password)
    print "Bugzilla connection: " + str(bz_connection.logged_in)

    # Build RFE query
    query = bz_connection.build_query(
        bug_id = bugs
    )
    bz_rfes = bz_connection.query(query)
    return bz_rfes, bz_connection

def create_requirements(bz_rfes, bz_connection):
    for bz_rfe in bz_rfes:
        bug_title, bug_product, named_parms, bug_description, bug_link, bug_id, bug_priority, bug_severity, bug_dfg = get_bug_params(bz_rfe)
        bug_title = "BZ_id=%s; %s" % (bug_id, bug_title)
        print "\n%s - start bug %s" % (datetime.datetime.now(), bug_id),
        print '"{}"'.format(bug_link)
        # Convert bugzilla to Polarion product and set
        product = PROJ_DICT[bug_product]
        if isRequirementInPolarion(bug_id, product) == False:
            #convert args, for now leave out Priority
            #named_parms["priority"] = PRIOR_DICT[bug_priority]
            named_parms["severity"] = SEV_DICT[bug_severity]
            # Set Polarion requirement type
            named_parms["reqtype"] = "functional"
            #Get bug description from first comment and add to Polarion requirement
            desc = ""
            if bug_description:
                desc = Text(bug_description.encode('ascii', 'ignore').decode('ascii'))
                # decode("utf-8"))
                desc.content_type = "text/plain"

            # Add hyperlink to bugzilla
            link = Hyperlink()
            link.role = "ref_ext"
            link.uri = bug_link

            for i in range(0,10): #WA for Polarion disconnection from time to time
                try:
                    req = Requirement.create(project_id=POLARION_PRODUCT, title=bug_title, desc=desc, **named_parms)
                    break
                except Exception as inst:
                    print inst
                    i+=1
                    time.sleep(10)

            req.add_hyperlink(link.uri, link.role)
            req.status = "approved"
            req.customerscenario = True
            req.update()

            #Get requirement ID and update bugzilla extrenal link tracker
            #gonna need to enable this back, but need a test project first
            #bz_connection.add_external_tracker(str(bz_rfe.id), str(req.work_item_id), ext_type_description="Polarion Requirement")
            #req_ids.append(req.work_item_id)

            print "%s - end bug: %s - %s" % (datetime.datetime.now(), req.work_item_id, link.uri)

if __name__ == "__main__":
    
    #takes a comma delimited string of bug ids with no spaces as the argument
    bugs = ""
    if len(sys.argv)>1:
        bugs = sys.argv[1]
    bz_rfes, bz_connection = get_rfes_from_bugzilla(bugs)
    print "Number of RFEs in " + BUGZILLA_VERSION + ": %s" %bz_rfes.__len__()
    create_requirements(bz_rfes, bz_connection)
    
    
    
    
    
