import asyncio
from app.twitch_rec.twitch_client import TwitchClient
from app.twitch_rec.streamer import Streamer
from app.twitch_rec.follower_network import FollowerNetwork
from app.twitch_rec.live_stream_info import LiveStreams
from app.twitch_rec.recommendation_pipeline import RecommendationPipeline
from app.twitch_rec.similarity import JaccardSim
from collections import OrderedDict


class Recommendation:
    sample_sz:      int = 300
    max_followings: int = 150
    min_mutual:     int = 3
    pipeline:       RecommendationPipeline
    similarities:   JaccardSim

    def __init__(self, streamer_name: str, max_followings: int = 150, min_mutual: int = 3) -> None:
        self.streamer = Streamer(name=streamer_name)
        self.folnet = FollowerNetwork(streamer_id=self.streamer.uid, min_mutual=min_mutual)
        self.live_streams = LiveStreams()

        self.max_followings = max_followings
        self.min_mutual = min_mutual


    async def __call__(self, n_consumers=100) -> dict:
        results = OrderedDict()

        async with TwitchClient() as tc:
            await self.streamer.create(tc)
            self.pipeline = RecommendationPipeline(self.streamer, self.folnet, self.live_streams)
            await self.pipeline(tc, n_consumers)

        ranked_sims = JaccardSim(self.folnet.mutual_followings, self.live_streams.total_followers).ranked_sim_scores
        print(ranked_sims)

        for uid in ranked_sims:
            print(self.live_streams.get(uid))

            results.update({uid: self.live_streams.get(uid)})

        print(results)

        await tc.close()

        return results

# live_list = {
#             usr['user_id']: {
#                      'name': usr['user_name'],
#                      'stream_title': usr['title'],
#                      'stream_url': 'https://www.twitch.tv/' + usr['user_name'],
#                      'thumbnail_url': usr['thumbnail_url'],
#                      'viewer_count': usr['viewer_count'],
#                      'stream_duration': duration(usr['started_at']),
#                      'lang': usr['language']
#                     }
#             for usr in live_list}


async def main():
    rec = Recommendation('emilybarkiss')
    await rec()

if __name__ == "__main__":
    asyncio.run(main())
