import asyncio
from app.settings import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
from twitchio.client import Client
from time import perf_counter
from itertools import chain


class TwitchClient(Client):
    
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        super().__init__(loop=self.loop, client_id=TWITCH_CLIENT_ID, client_secret=TWITCH_CLIENT_SECRET)
        self.http = self.http


    async def close(self):
        await self.http._session.close()


    async def get_total_followers(self, user_id):
        params = [('to_id', user_id)]
        return await self.http.request('GET', '/users/follows', params=params, count=True)


    async def get_total_followings(self, user_id):
        params = [('from_id', user_id)]
        return await self.http.request('GET', '/users/follows', params=params, count=True)


    async def get_n_followers(self, user_id, n_folls=300, wanted_full=False, params=None):
        params = params or []
        params.extend([('to_id', user_id)])
        return await self.http.request('GET', '/users/follows', params=params, limit=n_folls, full_reply=wanted_full)


    async def get_n_followings(self, user_id, n_folls=100,  wanted_full=False, params=None):
        params = params or []
        params.extend([('from_id', user_id)])
        return await self.http.request('GET', '/users/follows', params=params, limit=n_folls, full_reply=wanted_full)


    async def get_full_n_followers(self, user_id, n_folls=300, params=None):
        return await self.get_n_followers(user_id, n_folls, wanted_full=True, params=params)


    async def get_full_n_followings(self, user_id, n_folls=100, params=None):
        return await self.get_n_followings(user_id, n_folls, wanted_full=True, params=params)


    async def get_uids(self, *user_names: tuple):
        return [user.id for user in await self.get_users(*user_names)]


    async def get_uid(self, user_name):
        user = (await self.get_users(user_name))[0]
        return user.id


    async def get_streams(self, *, game_id=None, language=None, channels=None, limit=None):
        if not channels:
            await self.http.get_streams(game_id=game_id, language=language, channels=channels, limit=limit)

        if channels and len(channels) <= 100:
            return await self.http.get_streams(game_id=game_id, language=language, channels=channels, limit=limit)

        else:
            # split the list into chunks of size 100 & collect independently
            chunks = [channels[idx:idx+100] for idx in range(0, len(channels), 100)]
            streams = [self.get_streams(channels=chunk) for chunk in chunks]
            return list(chain.from_iterable(await asyncio.gather(*streams)))


    # async def get_streams_and_followers(self, uid_list):
    #     chunks = [uid_list[idx:idx+100] for idx in range(0, len(uid_list), 100)]
    #
    #     async def produce_live_streams(queue: asyncio.Queue, channel_list=uid_list):
    #         if not uid_list:
    #             raise AttributeError('No uid/channel list provided.')
    #
    #         async def put_queue(uids):
    #             [await queue.put(uids) for uid in uids]
    #
    #         # Get lists of live streams





async def main(name_list):
    tc = TwitchClient()

    # User IDs
    # uids = await tc.get_uids(*name_list)
    # print(f'User IDs: \n {uids}')

    # Followers
    # fols = await tc.get_followers(uids[0])
    # print(f'Followers: \n {fols}')

    # Followings
    # fols = await tc.get_following(uids[0])
    # print(f'Followings: \n {fols}')

    # Chatters
    # chatters = await tc.get_chatters(*name_list)
    # print(f'Chatters: \n {chatters}')

    # Streams
    streams = ['214560121', '50053663', '194434289', '234027306', '62371450', '99484944', '102688963', '87639782', '44424631', '250250773', '31688366', '142950704', '415249792', '255459250', '38594688', '203237367', '189647591', '224539819', '235511568', '181258781', '208840981', '201791804', '272748387', '264368048', '94101038', '145786272', '185619753', '89652468', '51270104', '26011012', '133705618', '405008403', '47606906', '192821942', '246450563', '83026310', '143559525', '39298218', '7920047', '110690086', '169179253', '182427515', '211234859', '40580009', '189651438', '206305288', '32140000', '61462782', '124197941', '44445592', '26991127', '263415726', '474475935', '81687332', '414885587', '197886470', '45143025', '19070311', '101400190', '60056333', '71092938', '36769016', '26490481', '84752541', '14408894', '118402338', '109620839', '421851579', '116333804', '93030465', '132083317', '35987962', '97014329', '45382480', '122673145', '115214051', '82524912', '254505950', '162412876', '55125740', '250045324', '140870994', '107611537', '76055616', '147881204', '48878319', '183837394', '218847732', '119257472', '189290002', '41245072', '64210215', '47641065', '53907383', '120750024', '195660234', '201171403', '506265929', '233300375', '193270950', '142651285', '53811294', '114856888', '120244187', '40781629', '486450344', '117379932', '223411175', '160447311', '49303276', '52091823', '240280475', '197822828', '65962492', '128410513', '57064460', '20993498', '38251312', '112375357', '96909659', '198860406', '31673862', '67955580', '274625', '87307183', '126436297', '106013742', '30080751', '24538518', '22253819', '29829912', '121203480', '66983298', '67650991', '38929725', '192678094', '32085830', '164026396', '226425431', '24991333', '76508554', '26261471', '168506484', '117927781', '198182340', '135326770', '181224914', '96419668', '61433001', '195187605', '222419086', '224145872', '32266685', '145785660', '212124784', '127651530', '39089007', '146790215', '101725379', '37402112', '196324887', '185617348', '206371413', '84331935', '45944269', '63986645', '198816206', '126913571', '199148685', '103191816', '70820966', '53967213', '101829198', '213633848', '59602620', '403745718', '218721301', '46973349', '223451253', '39724467', '15564828', '402117975', '128406716', '129171564', '211441494', '161355125', '225709389', '66742082', '128489946', '40375305', '197843018', '38953507', '29646658', '147665318', '121063510', '207412596', '141122650', '102461035', '38547166', '102777268', '36986060', '50191268', '88988716', '219338322', '70661496', '36935834', '205401621', '69239046', '27273690', '66728103', '38197393', '30417073', '185048086', '451544676', '98125665', '15554591', '29954462', '47764708', '44578737', '88547576', '231240827', '536898001', '210029646', '141022292', '135425835', '134084731', '450072444', '20131925', '226682404', '88575800', '475013048', '85872711', '130625652', '415781009', '204046683', '39938229', '69632935', '43859443', '72295650', '23172147', '119253305', '69772782', '408176508', '253558684', '42723961', '147748457', '105051098', '265522785', '107601977', '133051211', '40448252', '241743126', '52484898', '54440863', '41025762', '41411702', '28086682', '126846428', '94685332', '223528127', '35947566', '52819551', '417844294', '156920971', '193666399', '105533253', '117349875', '43981165', '109379351', '100506942', '106148834', '183988353', '56101690', '99427187', '166812739', '429837887', '68685842', '222855317', '179314556', '63992290', '142779073', '15386355', '85943836', '67143805', '198072135', '19571641', '44932815', '47456875', '190763447', '141661129', '97261888', '174703883', '63307680', '83538224', '182646246', '201060405', '151748592', '83014055', '274708557', '135161677', '94675393', '106125347', '203346720', '179339533', '212828302', '510161461', '232672264', '188058408', '61697069', '479702406', '141245005', '165794626', '238752081', '455462879', '173165156', '26758649', '41684297', '183663188', '106832731', '131275706', '24138907', '177730578', '40457029', '72548354', '402356183', '239272490', '41244221', '92112610', '206069041', '25093116', '214582852', '418095467', '142073418', '191350639', '125856916', '265567246', '72468070', '123637652', '213186672', '141188009', '162385621', '70483263', '151856979', '27107346', '38718052', '99192716', '161030195', '84432477', '105458682', '17337557', '28219022', '42867871', '239116628', '263831475', '273122285', '250883726', '125380746', '239916765', '134206255', '140321591', '50140697', '216065650', '161053067', '81997040', '266380015', '263643718', '433012616', '471391337', '232263892', '71422610', '145750386', '58704635', '103392969', '79777680', '229778046', '84473294', '142320628', '116228390', '23432410', '24147592', '198506129', '166279350', '65470540', '469162245', '66146219', '29080503', '66302775', '24865818', '189840471', '87959823', '51527197', '457977506', '111462736', '109673005', '480451648', '13884994', '475558372', '98253278', '125674251', '109697448', '245093162', '59312107', '256126044', '200020342', '188140767', '151592351', '107150633', '189957568', '250314729', '38553197', '40965449', '93878205', '29039515', '66262103', '68292748', '240804652', '124463659', '204976658', '219371486', '93053674', '154526718', '196137255', '403702327', '199056081', '271335354', '274881414', '12826', '6978352', '128892121', '188419071', '269835621', '106710521', '27121969', '9049063', '23417509', '12943173', '3481156', '51496027', '120597356', '21442544', '265430748', '105859614', '452469016', '77813150', '416137722', '46865623', '153489757', '185618927', '220173314', '240617539', '176315638', '76252345', '460227572', '137512364', '171005398', '441345826', '85511780', '147706309', '51813633', '215968422', '169093010', '193904342', '177475487', '53682763', '190915656', '260415346', '13240194', '21130533', '128697366', '176642237', '180800579', '168500992', '118241089', '90600924', '68313917', '163836275', '7352265', '128479231', '266398524', '87204022', '117736605', '206990465', '37201673', '194606944', '76026207', '60218498', '39011402', '18850094', '49940618', '66691674', '166484560', '140155598', '81593691', '172319488', '116910653', '175152654', '88946548', '228522821', '410848269', '26707340', '38244180', '101958817', '97280060', '51533859', '63880003', '16764225', '67802451', '136472868', '139538221', '63668620', '47947959', '87895435', '61839721', '23196698', '156567621', '184965345', '207385917', '79710628', '249973597', '39986770', '39276140', '84076430', '31963049', '56727273', '209199572', '408681839', '26903378', '48526626', '440446915', '452849164', '167160215', '69906737', '10207853', '402328438', '122407189', '142461251', '195219987', '121221937', '61106093', '225135452', '223696782', '144977942', '124326166', '87278100', '120134164', '65171890', '422315546', '213862351', '135202895', '100484450', '193437646', '56335545', '139472506', '198297465', '90309634', '59580613', '39627315', '171897087', '54706574', '197686699', '110176631', '427839729', '42583390', '278535193', '38199683', '45836039', '245962142', '271027486', '135051656', '25784746', '25653002', '42673406', '38881685', '14293484', '36029255', '54589395', '27934574', '28036688', '26946000', '463164824', '277720561', '273506632', '125387632', '181077473', '24070690', '267224297', '32569902', '201346683', '26929683', '99824406', '404319093', '46431370', '110892046', '210882637', '190110074', '79615025', '61482933', '53327800', '145270723', '7154733', '32526505', '30446023', '20087878', '212434564', '193797503', '189568053', '200630822', '155443590', '123042641', '459331509', '438619543', '197855687', '76385901', '46094501', '452059597', '482858163', '197525460', '132580358', '265135318', '52878372', '210524396', '139460091', '66566240', '212503406', '151445480', '73779954', '92160602', '195620340', '26301881', '451367545', '36858184', '102418287', '75346877', '71190292', '189755167', '55433748', '40112411', '129004732', '22578309', '38746172', '83080855', '127140941', '31239503', '121510236', '25690271', '113876662', '129342719', '135262775', '19942092', '42108204', '57744501', '93518952', '186140154', '32355126', '214046429', '151478291', '204497093', '87854281', '7252615', '221314370', '422914692', '280682466', '197338880', '239550929', '278362653', '84655119', '40934651', '116460040', '194196775', '47098493', '110240192', '32408610', '67962558', '73748917', '205383165', '216590269', '248553850', '192363734', '69993503', '193414501', '242069575', '35991862', '86268118', '129112562', '135719077', '111518512', '128335400', '54612707', '89102993', '46856676', '109552479', '432469595', '198558844', '238973795', '105008995', '191351978', '100373044', '227467763', '237976738', '218532507', '168708288', '161315772', '161550335', '214473744', '89117742', '437471269', '79936475', '116080489', '131718516', '146190302', '31582795', '23220337', '45044816', '198213921', '457626824', '47898306', '89771790', '119638640', '11001241', '97230482', '125384923', '50178655', '153820643', '27942990', '31557869', '38503140', '7832442', '32787655', '22510310', '131693310', '236420047', '232382754', '403049150', '136442286', '230440840', '73562336', '223896458', '231089942', '180094718', '63710292', '168829127', '189833032', '25085210', '41284990', '75987197', '216672046', '29961169', '423673952', '54506617', '213286008', '40980097', '179112208', '84198733', '22160589', '46490205', '92372244', '108945929', '64335053', '222097412', '238215138', '81918254', '164577907', '123360780', '451288627', '204471651', '31595348', '142717209', '222264107', '194886019', '237852859', '207580249', '181707977', '131865647', '70139535', '76789416', '206953837', '209397023', '44929591', '434386937', '151819490', '9679595', '150535812', '21736276', '156671675', '219270615', '228026450', '94130217', '273229896', '53853913', '253908987', '156037856', '51944529', '85531420', '77669901', '30079255', '4331474', '19654336', '265314628', '31430507', '191361872', '185933287', '194090650', '428694074', '196088251', '162937968', '83941878', '213331336', '22828727', '93589410', '38340208', '89524089', '50297139', '44858482', '103128180', '51875722', '47085237', '237767616', '146873643', '211220758', '69849568', '135149349', '169240378', '46337678', '147680823', '107943805', '45806740', '225850207', '231030802', '437870437', '439844899', '142050471', '198312595', '199624676', '103262684', '46415068', '138599634', '63221407', '57051641', '2083752', '56981354', '85399950', '5442330', '96276420', '217379662', '122320848', '40035700', '114049114', '58525651', '22484632', '147995860', '150842962', '51301985', '16943999', '102448835', '146992110', '110504495', '246218938', '85603763', '32521349', '116083177', '121941876', '28209837', '94753024', '254756234', '232402813', '240532806', '105020083', '190163874', '130624154', '143757089', '111799555', '119981767', '47528748', '65600543', '58659969', '421427837', '35630634', '99265185', '188483437', '45016942', '455628625', '221623988', '102966706', '79622099', '154752393', '183018122', '107032646', '421765865', '92986428', '95711949', '277945156', '180433291', '140554503', '76258299', '136765278', '43548655', '56728613', '38970168', '84550052', '155608413', '60442476', '264976441', '131070', '204708561', '266190741', '132660979', '127844094', '78556622', '157944149', '73840282', '79122704', '103848051', '31974228', '151071821', '277624494', '108268890', '140673115', '18587270', '59980349', '22561231', '203851512', '45832705', '241410018', '235989975', '92370369', '116010031', '57781936', '108005221', '74352492', '80603912', '175600466', '217633182', '59549865', '46383042', '49073484', '41726997', '15310631', '14836307', '89077758', '149747285', '30237250', '23458108', '45921770', '15832755', '189511607', '57307175', '132230344', '57292293', '23874126', '20711821', '71619346', '65664226', '3389768', '30409846', '31468943', '197559914', '524698414', '261660156', '64372897', '20702886', '68829581', '63809814', '137466653', '170214567', '30430463', '117544737', '419223633', '174311178', '23632986', '238213802', '134115908', '423630554', '190583809', '412538229', '202346918', '112822444', '11454896', '71928697', '415954300', '21588571', '93641995', '90020006', '136785688', '106065411', '145820017', '66520630', '127550308', '135165190', '197702129', '112751200', '108938909', '31747504', '56755261', '110751743', '265737184', '38148938', '55225490', '152046489', '274560902', '192858243', '66986103', '177305225', '102060247', '40972890', '41314239', '56395702', '109250560', '96963124', '163002495', '84139751', '279981815', '215327367', '58016964', '22053765', '38590324', '11249217', '141536993', '58383015', '70415000', '104882417', '273146935', '207660795', '49722413', '163233233', '245636860', '76980204', '52660871', '188882609', '110781296', '61478977', '180147909', '50817571', '46708418', '36858509', '440009035', '133505054', '20761874', '42481140', '129877185', '205558019', '223135349', '124510977', '117571593', '210469206', '158244839', '116921537', '108553544', '61744351', '88123348', '59290972', '51693898', '51858842', '66076836', '196383418', '23515233', '128738759', '86380282', '201015665', '9661257', '90222378', '48234453', '62568635', '57709221', '91628709', '109942562', '76330947', '239203452', '39585540', '38722829', '71370604', '180506306', '187610824', '160504245', '101845185', '58779994', '19703603', '70623724', '109069634', '36547945', '43028335', '173099843', '112793979', '43830727', '59635827', '69012069', '31478992', '137359733', '25458544', '230741578', '84574550', '177059558', '80352893', '155317812', '136354685', '124528806', '70863550', '240255583', '62134739', '73362563', '97982079', '250673065', '48225190', '65264217', '46533889', '65628081', '44566147', '29110452', '35642350', '175422065', '116825838', '31790129', '105916676', '57308790', '58839113', '56235100', '100048582', '72591872', '67772339', '194836962', '159973565', '200287794', '150236418', '241437135', '166412954', '181010304', '410201812', '110334150', '194476447', '57793021', '168697120', '41001374', '109223009', '140612343', '207585393', '77021066', '176958352', '43051595', '241383948', '135745876', '190821893', '210834025', '67872846', '87504695', '126521939', '80797758', '178238725', '70357283', '118573715', '31457014', '214314934', '192176749', '250019724', '78068008', '100462683', '163575952', '179954886', '26469355', '205228862', '86198803', '99641241', '113840021', '25640053', '81948622', '203591412', '46386566', '124420521', '90018770', '125700916', '23097521', '165917165', '37861628', '54785864', '66226143', '524589589', '31106024', '37736150', '24057992', '28243295', '70626480', '167402142', '136912983', '21302211', '132025128', '98520357', '83000199', '251749022', '474202951', '99390419', '495975208', '215050485', '209616330', '407947222', '401755696', '469790580', '114825211', '167346329', '217377982', '104157644', '55332579', '48478126', '67852884', '27184484', '140310387', '165895676', '49526600', '211700404', '23397860', '115207507', '134019465', '53533254', '234718913', '84579222', '108406086', '218139746', '23524577', '164716832', '214769693', '40256888', '51997047', '30692569', '135167681', '162252085', '232217', '195719409', '183665490', '154290246', '217355609', '110999237', '215934495', '461620880', '112591057', '25097408']
    print(f'> Original Length of streams: {len(streams)}')

    live_streams = await tc.get_streams(channels=streams)
    print(f'> Length of live_streams: {len(live_streams)}')
    print(f'Streams:\n  {live_streams}')

    # Cleanup open session sockets and event loops
    await tc.close()


if __name__ == "__main__":
    # test_names = ['stroopc', 'jitterted', 'strager']
    test_names = ['stroopc']

    start_time = perf_counter()
    asyncio.run(main(test_names))
    print(f'Run time: {round(perf_counter() - start_time, 3)} sec')

