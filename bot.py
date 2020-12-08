from telebot import TeleBot, types
import config
from ya_music import MyMusicClient

bot = TeleBot(token=config.token)
music_client = MyMusicClient()

info_button = types.ReplyKeyboardMarkup(resize_keyboard=True)
info_button.add(types.KeyboardButton('Help'))

user_status = {}


def get_inline_markup(lyrics=True, videos=True):
    markup = types.InlineKeyboardMarkup(row_width=3)
    lyrics_btn = types.InlineKeyboardButton('Lyrics', callback_data='lyrics')
    download_btn = types.InlineKeyboardButton('Download', callback_data='download')
    videos_btn = types.InlineKeyboardButton('Videos', callback_data='videos')
    btn_row = []
    if lyrics:
        btn_row.append(lyrics_btn)
    if videos:
        btn_row.append(videos_btn)
    btn_row.append(download_btn)
    markup.add(*btn_row)
    return markup


def send_audio(chat_id, track_id, track_name):
    path = f'assets/tracks/{track_name}.mp3'
    download_res = music_client.download_track(track_id, path)

    if download_res == 'ok':
        with open(path, 'rb') as f:
            try:
                bot.send_audio(chat_id=chat_id, audio=f)
            except Exception as e:  # request timeout
                bot.send_message(chat_id=chat_id, text=f'{e}\nTry again later.')
    else:
        bot.send_message(chat_id=chat_id, text=download_res)


def similar_track_answer(track_id, chat_id, choosed_name):
    # Sending message 'Tracks similar to *chosen track*' with markups (lyrics, videos, download)
    _supplement = music_client.get_supplement(track_id)
    has_lyrics = _supplement['full_lyrics'] is not None
    has_videos = False
    if _supplement['videos'] is not None:
        if not all(i['embed_url'] is None for i in _supplement['videos']):
            has_videos = True
    markup = get_inline_markup(has_lyrics, has_videos)
    choosed_track_msg = bot.send_message(chat_id, f'*Tracks similar to {choosed_name}:*',
                                         reply_markup=markup, parse_mode='Markdown')
    # Saving message btn to dictionary
    if 'markups' in user_status[chat_id]:
        user_status[chat_id]['markups'][choosed_track_msg.message_id] = track_id
    else:
        user_status[chat_id]['markups'] = {choosed_track_msg.message_id: track_id}
    print(user_status)

    # Sending similar tracks
    res = music_client.get_similar(track_id)
    options = res[0]
    if res[1] is not None:
        user_status[chat_id]['ids'] = res[1]
        poll_info = bot.send_poll(chat_id=chat_id, question=chat_id, options=options)
        user_status[chat_id]['poll_msg_id'] = poll_info.message_id
    else:
        bot.send_message(chat_id, res[0])  # No similar tracks found


@bot.message_handler(commands=['start'])
def welcome(message: types.Message):
    img = open('assets/welcome.png', 'rb')
    bot.send_photo(chat_id=message.chat.id,
                   photo=img,
                   caption=f'Welcome, *{message.from_user.first_name}*\n\n'
                           'Start with /search command and type a query\n\n'
                           'For example: */search Believer - Imagine Dragons*',
                   parse_mode='Markdown',
                   reply_markup=info_button)
    img.close()


@bot.message_handler(commands=['search'])
def search(message: types.Message):
    query = message.text.strip().split('/search')[1].strip()
    chat_id = message.chat.id
    text = None
    if query == '':
        text = 'It seems you forgot the request after the command. Tap "Help" for more details'
    elif len(query) < 5:
        text = 'Too short request'
    else:
        options, ids = music_client.search(query)

        # Adding to dictionary
        if chat_id not in user_status:
            user_status[chat_id] = {'ids': ids}  # do not need to state global (it is)
        else:
            user_status[chat_id]['ids'] = ids

        # Check if we have options (what if 1 option?)
        if not options:
            text = 'Nothing found. Try another query'
        elif len(options) == 1:  # if only 1 track found on search requests
            track_id = ids[0]
            track_name = options[0]
            similar_track_answer(track_id=track_id, chat_id=chat_id, choosed_name=track_name)
        else:
            poll_info = bot.send_poll(chat_id=chat_id, question=chat_id, options=options)
            user_status[chat_id]['poll_msg_id'] = poll_info.message_id

    print(user_status)
    if text is not None:
        bot.send_message(chat_id=chat_id, text=text)


@bot.message_handler(commands=['test'])
def test(message: types.Message):
    chat_id = message.chat.id
    options = ['Sapphire - Andy Hunter',
               'Hold Me Back - Marin Hoxha, Chris Linton',
               'Tell Me Why - Sound of Legend',
               'GRYFFIN, Slander, Calle Lehmann',
               'All You Need To Know']
    ids = ['10994777', '40133452', '48966383', '51385674']

    if chat_id not in user_status:
        user_status[chat_id] = {'ids': ids}  # do not need to state global (it is)
    else:
        user_status[chat_id]['ids'] = ids
    poll_info = bot.send_poll(chat_id=chat_id, question=chat_id, options=options)
    user_status[chat_id]['poll_msg_id'] = poll_info.message_id


@bot.poll_handler(lambda poll: not poll.is_closed)
def poll_answer(poll: types.Poll):
    votes = [i.voter_count for i in poll.options]
    choosed_id = votes.index(1)
    choosed_name = poll.options[choosed_id].text
    chat_id = int(poll.question)

    bot.stop_poll(chat_id, user_status[chat_id]['poll_msg_id'])
    track_id = user_status[chat_id]['ids'][choosed_id]

    similar_track_answer(track_id=track_id, chat_id=chat_id, choosed_name=choosed_name)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call: types.CallbackQuery):
    chat_id = int(call.message.chat.id)
    msg_id = call.message.message_id
    track_id = user_status[chat_id]['markups'][msg_id]

    if call.data == 'lyrics':
        lyrics = music_client.get_supplement(track_id)['full_lyrics']
        bot.send_message(chat_id, lyrics)
    elif call.data == 'download':
        # For example: 'Tracks similar to All I Wanted - Daughter:'
        track_name = call.message.text.split('Tracks similar to ')[1][:-1]
        send_audio(chat_id, track_id, track_name)
    elif call.data == 'videos':
        videos = music_client.get_supplement(track_id)['videos']
        video_urls = [i['embed_url'] for i in videos if i['embed_url'] is not None]
        print(video_urls)
        video_urls_str = '\n\n'.join(video_urls)
        bot.send_message(chat_id, video_urls_str)


@bot.message_handler(content_types=['text'])
def answer(message: types.Message):
    if message.text.lower() == 'help':
        msg = 'Start with /search command and enter the query\n\n' \
              'For example: */search Believer - Imagine Dragons*\n\n' \
              'You can choose then the index of the track in order ' \
              'to download it and found more similar tracks.'
    else:
        msg = 'Unknown command'
    bot.send_message(chat_id=message.chat.id, text=msg, parse_mode='Markdown')


if __name__ == '__main__':
    bot.polling(none_stop=True)
