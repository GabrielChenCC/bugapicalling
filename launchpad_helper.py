import os
from launchpadlib.launchpad import Launchpad
from launchpadlib.uris import LPNET_WEB_ROOT, STAGING_WEB_ROOT, \
    QASTAGING_WEB_ROOT

def collect_bug_information(bug_task):
    """ Collect bug informations

    Args:
        bug_task (object): Launchpad bug task object
    """

    bug_info = {
        "status": bug_task.status,
        "title": bug_task.title,
        "tags": " ".join(bug_task.bug.lp_get_parameter("tags")),
        "assignee": bug_task.assignee.name if bug_task.assignee else "",
        "importance": bug_task.importance
    }

    return bug_info

class LaunchpadAssistant():
    def __init__(self):
        # can be 'production', 'staging' or 'qastaging'
        service_root = os.environ.get(
            "APPORT_LAUNCHPAD_INSTANCE", "production")
        print("Using {} service root".format(service_root))

        directory = os.path.expanduser("~/.launchpadlib")
        if not os.path.isdir(directory):
            os.mkdir(directory)

        launchpad = Launchpad.login_with(
            "bugit",
            service_root,
            credentials_file=os.path.join(directory, "bugit"),
            allow_access_levels=["WRITE_PRIVATE"],
        )

        # Small trick to force access to launchpad and verify authentication
        launchpad.me
        self.launchpad = launchpad
        self.bug = None

    def search_bugs(self, project, cid):
        """ Search existing bugs in Launchpad by CID

        Args:
            project (string): Launchpad project name
            cid (string): CID of the device from C3
        """

        project = self.check_project_exist(project)
        try:
            print("Searching bugs by {}...".format(cid))
            bug_tasks = project.searchTasks(tags=[cid])
        except Exception:
            error_message = "Failed to search bugs by {}".format(cid)
            raise LaunchpadAssistantError(error_message)

        return [ (t.bug, collect_bug_information(t)) for t in bug_tasks ]

    def get_bug_information(self, bug_id):
        """ Get existing bug's informations from launchpad

        Args:
            bug_id (string): bug ID to retrive from launchpad
        """

        try:
            print("Checking bug...")
            self.bug = self.launchpad.bugs[bug_id]
        except Exception:
            error_message = "{} launchpad bug not found".format(bug_id)
            raise LaunchpadAssistantError(error_message)

        return self.bug, collect_bug_information(self.bug.bug_tasks[0])

    def check_project_exist(self, project_name):
        """ Check if given project name exist
        """

        try:
            print("Checking project name...")
            project = self.launchpad.projects[project_name]
        except Exception:
            error_message = "{} launchpad project not found".format(
                project_name)
            raise LaunchpadAssistantError(error_message)

        return project

    def check_series_exist(self, project, series_name):
        """ Check if given series name exist in the project
        """

        print("Checking series...")
        series = project.getSeries(name=series_name)
        if series is None:
            error_message = "{} series not found".format(series_name)
            raise LaunchpadAssistantError(error_message)

        return series

    def check_assignee_exist(self, assignee_name):
        """ Check if given assignee exist
        """

        try:
            print("Checking assignee...")
            assignee = self.launchpad.people[assignee_name]
        except Exception:
            error_message = "{} launchpad user not found".format(assignee_name)
            raise LaunchpadAssistantError(error_message)

        return assignee

    def create_bug(self, bug_dict):
        """Create issue to Launchpad with given informations

        Args:
            bug_dict (dict): Contain all information needed to creating a bug

        """
        # checking if the project is exist
        lp_project = None
        lp_project = self.check_project_exist(bug_dict['project'])

        # checking if the series is exist
        lp_series = None
        if bug_dict['series']:
            lp_series = self.check_series_exist(lp_project, bug_dict['series'])

        # checking if assignee is exist
        lp_assignee = None
        if bug_dict['assignee']:
            lp_assignee = self.check_assignee_exist(bug_dict['assignee'])

        if not self.bug:
            print("Creating Launchpad bug report...")
            self.bug = self.launchpad.bugs.createBug(
                title=bug_dict['title'],
                description=bug_dict['description'],
                tags=bug_dict['tags'].split(),
                target=lp_project
            )
            print("Bug report #{} created.".format(self.bug.id))
        else:
            print("Updating Launchpad bug report...")
            self.bug.title = self.lp_title
            self.bug.description = self.lp_description
            self.bug.tags = self.lp_tags.split()
            self.bug.lp_save()

        # Task configuration
        task = self.bug.bug_tasks[0]
        if self.bug and task.target != lp_project:
            print("Updating project...")
            task.target = lp_project
            task.lp_save()

        if lp_series:
            print("Setting series...")
            nomination = self.bug.addNomination(target=lp_series)
            nomination.approve()

        # We update bug info only for the latest created series
        task = self.bug.bug_tasks[len(self.bug.bug_tasks) - 1]
        if lp_assignee:
            print(f"Setting assignee for series {task.bug_target_name}...")
            task.assignee = lp_assignee
        print("Setting status...")
        task.status = bug_dict['status']
        print("Setting importance...")
        task.importance = bug_dict['priority']

        task.lp_save()

        service_root = os.environ.get(
            "APPORT_LAUNCHPAD_INSTANCE", "production")
        if service_root == "qastaging":
            bug_url = QASTAGING_WEB_ROOT + f"bugs/{self.bug.id}"
        elif service_root == "staging":
            bug_url = STAGING_WEB_ROOT + f"bugs/{self.bug.id}"
        else:
            bug_url = LPNET_WEB_ROOT + f"bugs/{self.bug.id}"

        print("Bug report #{} updated.".format(self.bug.id))
        print(bug_url)

        return self.bug, bug_url

    def upload_attachments(self, attachments):
        """Upload attachments to the issue

        Args:
            attachments (list): List of attachments
        """

        for a in attachments:
            print("Uploading attachment {}...".format(a))
            # bug = self.launchpad.bugs[bug_id]
            self.bug.addAttachment(
                comment="Automatically attached",
                filename=a,
                data=attachments[a]
            )

    def add_comment(self, comment):
        """Add comment to the bug
        """

        print("Adding comment...")
        self.bug.newMessage(content=comment)

    def update_bug(self, bug_dict):
        """Upload bug informations
        """

        bug_task = self.bug.bug_tasks[0]

        lp_assignee = None
        if bug_dict['assignee']:
            lp_assignee = self.check_assignee_exist(bug_dict['assignee'])
            print("Setting assignee to {}...".format(bug_dict['assignee']))
            bug_task.assignee = lp_assignee

        if bug_dict['status']:
            print("Setting status to {}...".format(bug_dict['status']))
            bug_task.status = bug_dict['status']
        if bug_dict['priority']:
            print("Setting priority to {}...".format(bug_dict['priority']))
            bug_task.importance = bug_dict['priority']
        if bug_dict['tags']:
            print("Setting tag...")
            self.bug.tags = bug_dict['tags'].split()

        self.bug.lp_save()
        bug_task.lp_save()

        service_root = os.environ.get(
            "APPORT_LAUNCHPAD_INSTANCE", "production")
        if service_root == "qastaging":
            bug_url = QASTAGING_WEB_ROOT + f"bugs/{self.bug.id}"
        elif service_root == "staging":
            bug_url = STAGING_WEB_ROOT + f"bugs/{self.bug.id}"
        else:
            bug_url = LPNET_WEB_ROOT + f"bugs/{self.bug.id}"

        print("Bug report #{} updated.".format(self.bug.id))

        return self.bug, bug_url


class LaunchpadAssistantError(Exception):
    """Raised when an error is reported during upload to Launchpad."""

    pass
