must have bugzilla connector and pylarion installed
BugZilla:
sudo pip install python-bugzilla

Pylarion:
and see this document for directions on setting up Pylarion
 Setup pylarion:
https://mojo.redhat.com/docs/DOC-1089423

This is what bugPlug.py does:

    reads the .pylarion config for the polarion deployment, the username and password
    this must work for both Polarion and Bugzilla.  This means the User IDs and PWs must work for both.  Also, the user id must work across all projects, so it probably needs to be a global admin ID 
    takes a comma delimited string of bugzilla bug_id's like "python bugPlug.py 1011755,1003044" 
        or we can do it some other way
    gets the information from bugzilla using the bugzilla connector
    checks to see if the bugs already have requirements created for them in Polarion
        if requirement exists then it does nothing
    if the requirement does not exist then it adds one by doing this:
        creates a new requirement
        converts Bugzilla severity to Polarion Severity
        Makes the requirement type functional
        converts the Bugzilla Product to a Polarion Project
        checks the customer scenario box
        marks it as approved
        create a hyper link with a link to the bugzilla bug_id
        prepends this to the title BZ_id=????;
        we have to do this because the hyperlink field is not queryable
        so this lets use check if they already exists.  This will also make it easy to do Lucene queries in Polarion.
    Adds the polarion requirement ID to the bugzilla bug_id using the bugzilla connector.
    TODO:  I am currenly not writing to the flag qe_test_coverage because I couldn't get the code to work.  See notes in the code itself.  However, for the example bug I was given this flag was already set, so maybe this is a moot point
  

