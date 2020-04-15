import asyncio
import os
from enum import Enum
from typing import List, Optional, Tuple

import pandas as pd
import pyjq
from aiohttp import ClientSession
from pydantic import Field

from toucan_connectors.common import nosql_apply_parameters_to_query
from toucan_connectors.toucan_connector import ToucanConnector, ToucanDataSource

from .constants import FILTER_DICTIONARY, MAX_RUNS, PER_PAGE
from .helpers import build_df, build_empty_df

BASE_ROUTE = f'https://proxy.bearer.sh/aircall_oauth'
BEARER_API_KEY = os.environ.get('BEARER_API_KEY')


async def fetch_page(
    base_endpoint: str, data_list: List[dict], session: ClientSession, limit, current_pass: int
) -> List[dict]:
    """
    Fetches data from AirCall API

    dependent on existence of other pages and call limit
    """
    data: dict = await fetch(base_endpoint, session)

    data_list.append(data)

    next_page_link = None
    meta_data = data.get('meta', None)

    if meta_data is not None:
        next_page_link: Optional[str] = data['meta'].get('next_page_link')

    current_pass += 1

    if next_page_link is not None and current_pass < limit:
        new_endpoint = next_page_link
        data_list = await fetch_page(new_endpoint, data_list, session, limit, current_pass)

    return data_list


async def fetch(new_endpoint, session: ClientSession) -> dict:
    """The basic fetch function"""
    async with session.get(new_endpoint) as res:
        return await res.json()


class AircallDataset(str, Enum):
    calls = 'calls'
    tags = 'tags'
    users = 'users'


class AircallDataSource(ToucanDataSource):
    limit: int = Field(MAX_RUNS, description='Limit of entries (default is 1 run)', ge=1)
    query: Optional[dict] = {}
    dataset: AircallDataset = 'users'


class AircallConnector(ToucanConnector):
    """
    This is a connector for [Aircall](https://developer.aircall.io/api-references/#endpoints)
    using [Bearer.sh](https://app.bearer.sh/)
    """

    data_source_model: AircallDataSource
    bearer_integration = 'aircall_oauth'
    bearer_auth_id: str

    async def _get_data(self, dataset: str, query, limit) -> Tuple[List[dict], List[dict]]:
        """Triggers fetches for data and does preliminary filtering process"""
        variable_endpoint = f'{BASE_ROUTE}/{dataset}?per_page={PER_PAGE}'
        headers = {'Authorization': BEARER_API_KEY, 'Bearer-Auth-Id': self.bearer_auth_id}
        async with ClientSession(headers=headers) as session:
            teams_endpoint = f'{BASE_ROUTE}/teams?per_page={PER_PAGE}'

            team_data, variable_data = await asyncio.gather(
                fetch_page(teams_endpoint, [], session, limit, 0,),
                fetch_page(variable_endpoint, [], session, limit, 0,),
            )

            team_jq_filter = FILTER_DICTIONARY.get('teams')
            variable_jq_filter = FILTER_DICTIONARY.get(dataset, 'users')

            team_data = pyjq.first(team_jq_filter, {'results': team_data})
            variable_data = pyjq.first(variable_jq_filter, {'results': variable_data})
            return team_data, variable_data

    async def _get_tags(self, dataset: str, query, limit) -> List[dict]:
        """Triggers fetches for tags and does preliminary filtering process"""
        variable_endpoint = f'{BASE_ROUTE}/{dataset}?per_page={PER_PAGE}'
        headers = {'Authorization': BEARER_API_KEY, 'Bearer-Auth-Id': self.bearer_auth_id}
        async with ClientSession(headers=headers) as session:
            raw_data = await fetch_page(variable_endpoint, [], session, limit, 1,)
            jq_filter = FILTER_DICTIONARY.get(dataset, 'tags')

            return pyjq.first(jq_filter, {'results': raw_data})

    def run_fetches(self, dataset, query, limit) -> Tuple[List[dict], List[dict]]:
        """sets up event loop and fetches for 'calls' and 'users' datasets"""
        # try:
        #     loop = asyncio.get_event_loop()
        # except RuntimeError:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(self._get_data(dataset, query, limit))
        return loop.run_until_complete(future)

    def run_fetches_for_tags(self, dataset, query, limit):
        """sets up event loop and fetches for 'tags' dataset"""
        # try:
        #     loop = asyncio.get_event_loop()
        # except RuntimeError:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(self._get_tags(dataset, query, limit))
        return loop.run_until_complete(future)

    def _retrieve_data(self, data_source: AircallDataSource) -> pd.DataFrame:
        """retrieves data from AirCall API"""
        query = nosql_apply_parameters_to_query(data_source.query, data_source.parameters)
        dataset = data_source.dataset
        empty_df = build_empty_df(dataset)

        # NOTE: no check needed on limit here because a non-valid limit
        # raises a Pydantic ValidationError
        limit = data_source.limit

        if dataset == 'tags':
            res = self.run_fetches_for_tags(dataset, query, limit)
            non_empty_df = pd.DataFrame(res)
            return pd.concat([empty_df, non_empty_df])
        else:
            team_data, variable_data = self.run_fetches(dataset, query, limit)
            return build_df(
                dataset, [empty_df, pd.DataFrame(team_data), pd.DataFrame(variable_data)]
            )
