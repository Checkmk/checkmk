# -*- encoding: utf-8
# yapf: disable


checkname = 'jenkins_jobs'


freeze_time = '2019-09-09T14:19:00'


info = [[u'[{"healthReport": [], "displayNameOrNull": "TEST DISPLAY NAME", "_class": "com.cloudbees.hudson.plugins.folder.Folder", "jobs": [{"healthReport": [], "displayNameOrNull": "My Folder 2", "_class": "com.cloudbees.hudson.plugins.folder.Folder", "jobs": [{"healthReport": [], "displayNameOrNull": "My Folder 3", "_class": "com.cloudbees.hudson.plugins.folder.Folder", "jobs": [{"name": "Project3", "color": "notbuilt", "lastSuccessfulBuild": null, "healthReport": [], "displayNameOrNull": null, "lastBuild": null, "_class": "hudson.model.FreeStyleProject"}], "name": "Folder3"}, {"name": "Project2", "color": "notbuilt", "lastSuccessfulBuild": null, "healthReport": [], "displayNameOrNull": null, "lastBuild": null, "_class": "hudson.model.FreeStyleProject"}], "name": "Folder2"}, {"name": "Project1", "color": "blue", "lastSuccessfulBuild": {"timestamp": 1568029334960, "_class": "hudson.model.FreeStyleBuild"}, "healthReport": [{"score": 100}], "displayNameOrNull": "My Project 1", "lastBuild": {"duration": 98, "timestamp": 1568029334960, "_class": "hudson.model.FreeStyleBuild", "number": 1, "result": "SUCCESS"}, "_class": "hudson.model.FreeStyleProject"}], "name": "Folder1"}]']]


discovery = {'': [(u'Folder1/Folder2/Folder3/Project3', {}),
                  (u'Folder1/Folder2/Project2', {}),
                  (u'Folder1/Project1', {})]}


checks = {'': [(u'Folder1/Folder2/Folder3/Project3',
                {},
                [(0, u'State: Notbuilt', [])]),
               (u'Folder1/Folder2/Project2', {}, [(0, u'State: Notbuilt', [])]),
               (u'Folder1/Project1',
                {},
                [(0, u'Display name: My Project 1', []),
                 (0, u'State: Blue', []),
                 (0,
                  'Job score: 100%',
                  [('jenkins_job_score', 100, None, None, None, None)]),
                 (0,
                  'Time since last successful build: 156 m',
                  [('jenkins_time_since',
                    9405.039999961853,
                    None,
                    None,
                    None,
                    None)]),
                 (0, 'Last build at: 2019-09-09 13:42:14', []),
                 (0, 'Build id: 1', []),
                 (0,
                  u'Build duration: 98.0 ms',
                  [('jenkins_build_duration', 0.098, None, None, None, None)]),
                 (0, u'Build result: Success', [])])]}