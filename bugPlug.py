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
PROJ_DICT = {"test": "Polarion",
    "Red Hat Cluster Suite": "RHELOpenStackPlatform",
    "Container Development Kit": "CMP",
    "Container Native Vitualization": "CNV",
    "Red Hat Virtualization": "RHEVM3",
    "OVirt": "RHEVM3",
    "OpenShift Container platform": "OSE",
    "Openshift Online": "OSOP",
    "Red Hat Ceph Storage": "CEPH",
    "Red Hat CloudForms Management Engine": "CloudForms",
    "Red Hat Enterprise Linux 5": "RedHatEnterpriseLinux7",
    "Red Hat Enterprise Linux 7": "RedHatEnterpriseLinux7",
    "Red Hat Enterprise Linux 8": "RedHatEnterpriseLinux7",
    "Red Hat Software Collection": "RedHatEnterpriseLinux7",
    "Red Hat Enterprise Linux 6": "RHEL6",
    "Red Hat Gluster Storage": "RHG3",
    "Red Hat OpenStack": "RHELOpenStackPlatform",
    "Red Hat Quickstart Cloud Installer": "QuickstartCloudInstaller",
    "Red Hat Satellite 6": "RHSAT6"}

class ConfigFileMissingException(Exception):
    pass


def convert_polarion_dfg(bug_dfg):
    dfg_id = ""
    if bug_dfg.startswith("DFG:Ceph"):
        dfg_id = "24"
    elif bug_dfg.startswith("DFG:Compute"):
        dfg_id = "6"
    elif bug_dfg.startswith("DFG:CloudApp"):
        dfg_id = "23"
    elif bug_dfg.startswith("DFG:Containers"):
        dfg_id = "25"
    elif bug_dfg.startswith("DFG:DF"):
        dfg_id = "7"
    elif bug_dfg.startswith("DFG:HardProv"):
        dfg_id = "9"
    elif bug_dfg.startswith("DFG:Infra"):
        dfg_id = "5"
    elif bug_dfg.startswith("DFG:MetMon"):
        dfg_id = "27"
    elif bug_dfg.startswith("DFG:NFV"):
        dfg_id = "11"
    elif bug_dfg.startswith("DFG:Networking"):
        dfg_id = "10"
    elif bug_dfg.startswith("DFG:ODL"):
        dfg_id = "3"
    elif bug_dfg.startswith("DFG:OVN"):
        dfg_id = "17"
    elif bug_dfg.startswith("DFG:OpsTools"):
        dfg_id = "4"
    elif bug_dfg.startswith("DFG:PIDONE"):
        dfg_id = "19"
    elif bug_dfg.startswith("DFG:ReleaseDelivery"):
        dfg_id = "13"
    elif bug_dfg.startswith("DFG:Security"):
        dfg_id = "14"
    elif bug_dfg.startswith("DFG:Storage"):
        dfg_id = "15"
    elif bug_dfg.startswith("DFG:Telemetry"):
        dfg_id = "16"
    elif bug_dfg.startswith("DFG:UI"):
        dfg_id = "8"
    elif bug_dfg.startswith("DFG:Upgrades"):
        dfg_id = "22"
    elif bug_dfg.startswith("DFG:Workflows"):
        dfg_id = "28"
    elif bug_dfg.startswith("DFG:OpenShiftonOpenStack"):
        dfg_id = "26"
    else:
        dfg_id = ""

    return dfg_id

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
    #i was wrong you can search on hyperlink like this
    #select tc.c_id from WORKITEM tc inner join PROJECT on PROJECT.C_URI = tc.FK_URI_PROJECT left join struct_workitem_hyperlinks hlink on tc.c_uri=hlink.fk_uri_p_workitem where PROJECT.C_ID = 'Polarion' and tc.C_TYPE = 'requirement' and hlink.c_url LIKE '%1011755%'
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
    
    #used for local testing
    #if bugs == "":
        #bugs = "1517272" #,1011755,1003044" #1517272"#,
    
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
            
            #Convert DFG name from bugzilla to dfg_id in Polarion
            named_parms["d_f_g"] = convert_polarion_dfg(bug_dfg)
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
                    req = Requirement.create(project_id=product, title=bug_title, desc=desc, **named_parms)
                    break
                except Exception as inst:
                    print inst
                    i+=1
                    time.sleep(10)

            req.add_hyperlink(link.uri, link.role)
            req.status = "approved"
            req.customerscenario = True
            req.update()

            #[Anjali] one last step here is 'set 'qe-test-coverage' flag in Bugzilla (to show that the bugzilla has a test coverage)
            bz_connection.add_external_tracker(str(bz_rfe.id), str(req.work_item_id), ext_type_description="Polarion Requirement")
            custflag = {'qe_test_coverage': '-'}
            #doesn't matter if we send bugs as a list or not as the method fixes it anyway  
            #this currently does not work it returns an error, so I am disabling it
            #Fault -32000: 'Not an ARRAY reference at /var/www/html/bugzilla/Bugzilla/WebService/Util.pm line 44.\n
            #bz_connection.update_flags([bug_id], custflag)
            
            print "%s - end bug: %s - %s" % (datetime.datetime.now(), req.work_item_id, link.uri)

if __name__ == "__main__":
    
    #takes a comma delimited string of bug ids with no spaces as the argument
    bugs = ""
    if len(sys.argv)>1:
        bugs = sys.argv[1]
    bz_rfes, bz_connection = get_rfes_from_bugzilla(bugs)
    print "Number of RFEs in " + BUGZILLA_VERSION + ": %s" %bz_rfes.__len__()
    create_requirements(bz_rfes, bz_connection)
    
       
    
