__author__ = 'Mohammed Hamdy'

from os.path import dirname, join, splitext, basename
from os import listdir
from random import choice
from datetime import datetime
import csv, subprocess, sys

_config_dir = join(dirname(dirname(__file__)), "config")

def dispense_pellet():
  batch_despenser = join(_config_dir, "dispenser.bat")
  process = subprocess.Popen(batch_despenser, stdout=subprocess.PIPE)
  output = process.communicate()
  sys.stderr.write(str(output))

def get_video_dir():
  return join(dirname(dirname(__file__)), "res", "videos")

def get_images_dir():
  return join(dirname(dirname(__file__)), "res", "images")

def get_background_placeholder():
  return join(get_images_dir(), "placeholder.png")

class SubjectManager(object):
  """
  Keeps track of subjects and conditions. Like which conditions has been run for each subject.
  It also has convenience methods for working with subjects
  """

  def __init__(self):
    self._subjects_file_path = join(dirname(dirname(__file__)), "config", "subjects.csv")
    dir_conditions = get_video_dir()
    self._subject_to_conditions_map = {}
    self._full_path_videos = [join(dir_conditions, video_name) for video_name in listdir(dir_conditions)]
    subjects_csv_reader = csv.reader(open(self._subjects_file_path, 'r', newline=''))
    for row in subjects_csv_reader:
      subject_name = row[0]
      subject_played_conditions = []
      for played_condition_name in row[1:]:
        for path_video in self._full_path_videos:
          if played_condition_name in path_video:
            subject_played_conditions.append(path_video)
      self._subject_to_conditions_map[subject_name] = subject_played_conditions

  def get_subjects(self):
    return self._subject_to_conditions_map.keys()

  def get_conditions(self, subject):
    return self._subject_to_conditions_map[subject]

  def is_subject_done(self, subject):
    return len(self._subject_to_conditions_map[subject]) == 4

  def get_condition(self, subject):
    # assign a random condition not before assigned to subject
    subject_played_conditions = self._subject_to_conditions_map[subject]
    non_played_conditions = list(set(self._full_path_videos) - set(subject_played_conditions))
    condition_video_path = choice(non_played_conditions)
    subject_played_conditions.append(condition_video_path)
    return Condition(condition_video_path)

  def save(self):
    # this should be called at the end of each condition (200 trials)
    with open(self._subjects_file_path, 'w', newline='') as subjects_writer:
      subjects_csv_writer = csv.writer(subjects_writer)
      for subject, conditions in self._subject_to_conditions_map.items():
        video_names = [splitext(basename(condition))[0] for condition in conditions]
        subjects_csv_writer.writerow([subject] + list(video_names))

def variablize_string(s):
  # convert "Hello World" to "hello_world"
  return s.lower().replace(' ', '_')

class Condition(object):

  def __init__(self, video):
    video_name = splitext(basename(video))[0]
    self.name = ' '.join([word.capitalize() for word in video_name.split('_')])
    self.video = video

  def get_associated_images(self):
    # each condition has 2 associated images.
    image_dir = get_images_dir()
    if "high_ranking" in self.video:
      return {"left_image":join(image_dir, "bluecogs.png"), "right_image":join(image_dir, "purpleleaf.png")}
    elif "low_ranking" in self.video:
      return {"left_image":join(image_dir, "redwhitesquares.png"), "right_image":join(image_dir, "irishgreen.png")}
    elif "stranger" in self.video:
      return {"left_image":join(image_dir, "greenbrownleaves.png"), "right_image":join(image_dir, "moon.png")}
    elif "nonsocial" in self.video:
      return {"left_image":join(image_dir, "purplediamond.png"), "right_image":join(image_dir, "snowflake.png")}

class TrialData(object):

  def __init__(self, subject, trial_index, condition):
    trial_datetime = datetime.now()
    self.date = trial_datetime.strftime("%m-%d-%y")
    self.time = trial_datetime.strftime("%H:%M:%S %p")
    self.subject = subject
    self.condition = condition
    self.trial_index = trial_index
    self.background_touches = 0
    self.video_touches = 0
    self.time_till_selection = None
    self.card_selected = None