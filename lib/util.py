__author__ = 'Mohammed Hamdy'

from os.path import dirname, join, splitext, basename
from os import listdir
from random import choice
from datetime import datetime
import json, subprocess

_config_dir = join(dirname(dirname(__file__)), "config")

def dispense_pellet():
  batch_despenser = join(_config_dir, "dispenser.bat")
  subprocess.Popen(batch_despenser, stdout=subprocess.PIPE)

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

  def __init__(self, total_trial_count):
    self._total_trial_count = total_trial_count
    self._subjects_file_path = join(dirname(dirname(__file__)), "config", "subjects.json")
    dir_conditions = get_video_dir()
    self._full_path_videos = [join(dir_conditions, video_name) for video_name in listdir(dir_conditions)]
    self._subject_infos = json.load(open(self._subjects_file_path, 'r', newline=''))

  def get_subjects(self):
    return [subject["name"] for subject in self._subject_infos]

  def get_conditions(self, subject):
    subject_info = self._get_subject_info(subject)
    video_paths = []
    for condition_name in subject_info.get("played_conditions", []):
      for condition_video in self._full_path_videos:
        if condition_name in condition_video:
          video_paths.append(condition_video)
    return video_paths

  def is_subject_done(self, subject):
    subject_info  = self._get_subject_info(subject)
    return len(self._get_playable_conditions(subject_info)) == 0

  def get_unfinished_condition(self, subject):
    # assign a random condition not before assigned to subject. the condition should also be unfinished
    # this assumes that the caller knows what it's doing. it won't check if there's no conditions left
    subject_info = self._get_subject_info(subject)
    playable_conditions = self._get_playable_conditions(subject_info)
    played_conditions = subject_info.setdefault("played_conditions", {})
    condition_video_path = playable_conditions[0] # choose highest priority (last_played) or just first
    # update the played condition
    # read the existing trial index or zero out
    condition_name = self._condition_name_from_video(condition_video_path)
    for condition, condition_desc in played_conditions.items():
      if condition == condition_name:
        next_trial_index = condition_desc["next_trial_index"]
        break
    else:
      next_trial_index = 0
    # the last_played property should only exist for a single condition
    played_conditions[condition_name] = {"next_trial_index": next_trial_index, "last_played": True}
    return Condition(condition_video_path, next_trial_index)

  def passed_trial(self, subject, condition):
    # should be called whenever a subject passes a trial
    subject_info = self._get_subject_info(subject)
    condition_info = subject_info["played_conditions"][self._condition_name_from_video(condition.video)]
    condition_info["next_trial_index"] += 1
    # remove resumption possibility from condition when it's finished
    if condition_info["next_trial_index"] == self._total_trial_count:
      condition_info.pop("last_played", None)

  def save(self):
    # this should be called at the end of each condition (200 trials)
    with open(self._subjects_file_path, 'w', newline='') as subjects_writer:
      json.dump(self._subject_infos, subjects_writer)

  def _get_subject_info(self, subject):
    for subject_info in self._subject_infos:
      if subject_info["name"] == subject:
        return subject_info

  def _get_playable_conditions(self, subject_info):
    # playable conditions are conditions never before played or has a trial index less than total trial count
    # this returns the list of video names that can be played
    playable_conditions = []
    # first add never before played conditions
    subject_played_condition_names = list(subject_info.get("played_conditions", {}).keys())
    for full_path_video in self._full_path_videos:
      condition_name = self._condition_name_from_video(full_path_video)
      if condition_name in subject_played_condition_names:
        condition_info = subject_info["played_conditions"][condition_name]
        next_trial_index = condition_info.get("next_trial_index", 0)
        last_played = condition_info.get("last_played", False)
        if next_trial_index < self._total_trial_count:
          playable_conditions.append(full_path_video)
        elif last_played:
          # give last played condition a priority by inserting it first into playable conditions
          playable_conditions.insert(0, full_path_video)
      else:
        # never before played condition
        playable_conditions.append(full_path_video)
    return playable_conditions

  def _condition_name_from_video(self, video_path):
    return splitext(basename(video_path))[0]

def variablize_string(s):
  # convert "Hello World" to "hello_world"
  return s.lower().replace(' ', '_')

class Condition(object):

  def __init__(self, video, next_trial_index=0):
    video_name = splitext(basename(video))[0]
    self.name = ' '.join([word.capitalize() for word in video_name.split('_')])
    self.video = video
    self.next_trial_index = next_trial_index

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
    self.pellets_dispensed = 0