import json
import traceback
from enum import Enum
from logging import DEBUG, StreamHandler, getLogger

import pandas as pd
import requests
from apiclient.discovery import build
from google.cloud import datastore

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class PandasWrapper(object):

  __instance = None

  def __new__(cls, *args, **keys):
    if cls.__instance is None:
      cls.__instance = object.__new__(cls)
    return cls.__instance

  def __init__(self, project_id):
    self.datastore_client = datastore.Client(project_id)

  def dataframe_to_datastore(self, df, datastore_kind_name=None, update_keys=None, over_write=False):

    logger.debug("datastore_kind_name:" + str(datastore_kind_name))
    logger.debug("update_keys:" + str(update_keys))

    if datastore_kind_name is None or datastore_kind_name == "":
      return

    for index, row in df.iterrows():
      query = self.datastore_client.query(kind=datastore_kind_name)
      if update_keys is not None and isinstance(update_keys, list):
        for k in update_keys:
          query.add_filter(k, '=', row[k])

      query_iter = query.fetch()
      result = list(query_iter)
      task = datastore.Entity(self.datastore_client.key(datastore_kind_name))

      if len(result) > 0:
        task = result[0]
        logger.debug("update:" + str(task))
        if not (over_write):
          continue
      else:
        logger.debug("insert:" + str(task))

      for col_name in df.columns:
        val = None
        if row[col_name] is not None:
          if isinstance(row[col_name], str):
            val = row[col_name][:1500]
          else:
            val = row[col_name]
        task[col_name] = val

      logger.debug("task:" + str(task))
      self.datastore_client.put(task)

  def set_diff_dataframes(self, df, df2, join_keys=None):

    init_column_name_list = df.columns
    df = df.merge(df2, on=join_keys, how='left')
    column_name_list = df.columns
    is_null_col_name = None
    for c in column_name_list:
      if "_y" in c:
        c_ = c.replace("_y", "")
        if c_ not in join_keys:
          is_null_col_name = c
          break

    df = df[df[is_null_col_name].isnull()]
    logger.debug("excluded_df.count:" + str(len(df)))
    column_name_list = df.columns
    for c in column_name_list:
      if "_x" in c:
        c_ = c.replace("_x", "")
        df = df.rename(columns={c: c_})
    column_name_list = df.columns
    drop_cols = list(set(column_name_list) - set(init_column_name_list))
    df = df.drop(drop_cols, axis=1)
    return df
