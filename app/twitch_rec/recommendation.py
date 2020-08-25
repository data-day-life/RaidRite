import asyncio
from app.twitch_rec.twitch_client import TwitchClient
from app.twitch_rec.streamer import Streamer
from app.twitch_rec.follower_network import FollowerNetwork
from app.twitch_rec.live_stream_info import LiveStreams
from app.twitch_rec.recommendation_pipeline import RecommendationPipeline
from app.twitch_rec.similarity import JaccardSim
from collections import OrderedDict
from app.twitch_rec.colors import Col


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

        mutual_followings, tot_followers = self.folnet.mutual_followings, self.live_streams.total_followers
        num_collected = self.pipeline.folnet_pipe.num_collected
        ranked_sims = JaccardSim(mutual_followings, tot_followers, num_collected).ranked_sim_scores
        # print(ranked_sims)

        for uid in ranked_sims:
            got = self.live_streams.get(uid)
            formatted = f'\n' \
                        f'{got["user_name"]:>18}  ' \
                        f'{got["viewer_count"]:>4}  ' \
                        f'{got["stream_duration"]:>10}   ' \
                        f'{got["language"]:>2}  ' \
                        f'{got["total_followers"]:>4}  ' \
                        f'{ranked_sims.get(uid)*100:.3f}  ' \
                        f'{mutual_followings.get(uid):>3}'


            print(formatted)
            # print(self.live_streams.get(uid))
            results.update({uid: self.live_streams.get(uid)})

        # print(results)

        await tc.close()

        return results

    def displ_fmt(self, name, viewers, duration, lang, total_folls, sim_score, mutual_count):
        pass


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
    from time import perf_counter
    t = perf_counter()

    rec = Recommendation('emilybarkiss')
    await rec()
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')

if __name__ == "__main__":
    asyncio.run(main())
