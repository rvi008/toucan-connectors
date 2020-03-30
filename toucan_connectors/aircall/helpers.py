"""Module containing helpers for the Aircall connector"""

import pandas as pd

from typing import List

from .constants import COLUMN_DICTIONARY, FILTER_DICTIONARY


def build_df(dataset: str, list_of_data: List[dict]) -> pd.DataFrame:
    """builds a dataframe for the users and calls datasets"""
    if dataset == 'users':
        return (pd
                .concat(list_of_data, sort=False, ignore_index=True)
                .drop_duplicates(['user_id'], keep='first')
                .assign(**{'user_created_at': lambda x: x['user_created_at'].str[:10]})
                )
    elif dataset == 'calls':
        empty_df, team_data, call_data = list_of_data
        df = (team_data
              .merge(call_data, sort=False, on='user_id', how='right')
              .drop(columns=['user_name_y', 'user_created_at']))

        total_df = (pd
                    .concat([empty_df, df], sort=False, ignore_index=True)
                    .assign(**{
                        'answered_at' : lambda t: pd.to_datetime(t['answered_at'], unit='s'),
                        'ended_at' : lambda t: pd.to_datetime(t['ended_at'], unit='s'),
                        'day' : lambda t : t['ended_at'].astype(str).str[:10]
                    })
                    # .rename(columns={'user_name_x' : 'user_name'})
                    )
        return total_df[COLUMN_DICTIONARY[dataset]]


def build_empty_df(dataset: str) -> pd.DataFrame:
    """Provides column headers for empty dataframes"""
    return pd.DataFrame(columns=COLUMN_DICTIONARY[dataset])


def generate_multiple_jq_filters(dataset: str) -> List[str]:
    """
    Provides two separate jq filters;
    used in calls and users datasets
    """

    teams_jq_filter: str = FILTER_DICTIONARY['teams']

    # NOTE: 'users' is the default dataset
    variable_jq_filter: str = FILTER_DICTIONARY.get(dataset, FILTER_DICTIONARY['users'])

    return [teams_jq_filter, variable_jq_filter]


def generate_tags_filter(dataset: str) -> str:
    """Provides a single, simple jq filter; only for tags call"""
    return FILTER_DICTIONARY.get(dataset, 'tags')
