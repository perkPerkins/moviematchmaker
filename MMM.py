import urllib
import requests
from bs4 import BeautifulSoup
import random
import urllib.parse


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content':  output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------
def parse_movie_strings(movie_array):
    del movie_array[0:12]
    release_date = movie_array.pop(len(movie_array) - 1)
    translate_table = dict.fromkeys(map(ord, '\':()!'), None)
    release_date = release_date.translate(translate_table)

    for x in range(len(movie_array)):
        movie_array[x] = movie_array[x].translate(translate_table)

    return [movie_array, release_date]
    
    
def generate_response(movie_array, intent, genre):
    samplesFile = open('responseSamples.txt', 'r')
    responseSamples = samplesFile.readlines()
    random_num = random.randint(0, len(movie_array) - 1)
    movie = ' '.join(movie_array[random_num][0])

    response = responseSamples[random.randint(0, len(responseSamples) - 1)]
    response = response.replace("\n", "")
    response = response.replace("$", movie)
    response = response.replace("#", genre)

    if int(movie_array[random_num][1]) < 2000:
        old_movie_file = open('<2000.txt', 'r')
        old_movie_responses = old_movie_file.readlines()
        response += old_movie_responses[random.randint(0, len(old_movie_responses) - 1)]
        response = response.replace("\n", "")
    
    response += " Have you seen this one yet?"
    return [response, movie]

def delete_actor_names(summary):
    summary = list(summary)
    for char in summary:
        if char == '(':
            index = summary.index('(')
            summary.pop(index)
            while char != ')':
                char = summary.pop(index)

    return ''.join(summary)

def error_handling(session, intent):

    if len(session) <= 4:  # if session does not contain the 'attributes' list, because user requests movie while starting the skill
        return get_welcome_response()
    if session['attributes']['previous_intent'] == "get_movie_response":
        movie = session['attributes']['movie']
        speech_output = "Sorry, I didn't catch that. Have you seen the movie " + movie + " yet?"
        session_attributes = {"previous_intent": "get_movie_response", "movie": movie, "genre": session['attributes']['genre'], "response_genre": session['attributes']['response_genre'], "another_movie": "None"}
    
    elif session['attributes']['previous_intent'] == "YesNo":
    
        if session['attributes']['another_movie'] == "None":
            speech_output = "Sorry, I didn't catch that. Did you want to hear a description of the plot for the movie " + session['attributes']['movie'] + "?"
            session_attributes = {"previous_intent": "YesNo", "genre": session['attributes']['genre'], "movie": session['attributes']['movie'], "response_genre": session['attributes']['response_genre'], "another_movie": "None"}
    
        else:
            speech_output = "Sorry, I didn't catch that. Did you want me to find you another movie?"
            session_attributes = {"previous_intent": "YesNo", "genre": session['attributes']['genre'], "response_genre": session['attributes']['response_genre'], "another_movie": "NotNone"}
    else:
        session_attributes = {}
        speech_output = "Sorry, I didn't catch that. What movie genre did you want?"
    
    card_title = "error_handling"
    reprompt_text = speech_output
    should_end_session = False
    
    return build_response(session_attributes, build_speechlet_response(
    card_title, speech_output, reprompt_text, should_end_session))

def get_movie_response(session, intent, another_movie = None, genre = None, response_genre = None):
    card_title = "genre"
    if genre is None:
        
        genres = []
        response_genres = []
        genre_found = False
        if len(intent['slots']['genreOne']) > 2:
            if intent['slots']['genreOne']['resolutions']['resolutionsPerAuthority'][0]['status']['code'] == "ER_SUCCESS_MATCH":
                genres.append(intent['slots']['genreOne']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name'])
                response_genres.append(intent['slots']['genreOne']['value'])
                genre_found = True
        
        if len(intent['slots']['genreTwo']) > 2:
            if intent['slots']['genreTwo']['resolutions']['resolutionsPerAuthority'][0]['status']['code'] == "ER_SUCCESS_MATCH":
                genres.append(intent['slots']['genreTwo']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name'])
                response_genres.append(intent['slots']['genreTwo']['value'])
                genre_found = True
        
        if len(intent['slots']['genreThree']) > 2:
            if intent['slots']['genreThree']['resolutions']['resolutionsPerAuthority'][0]['status']['code'] == "ER_SUCCESS_MATCH":
                genres.append(intent['slots']['genreThree']['resolutions']['resolutionsPerAuthority'][0]['values'][0]['value']['name'])
                response_genres.append(intent['slots']['genreThree']['value'])
                genre_found = True
        
        if not genre_found:
            return error_handling(session, intent)

        random_num = random.randint(0, len(genres) - 1)
        genre = genres[random_num]
        response_genre = response_genres[random_num]
    
    genre = genre.split()
    
    if len(genre) > 1:
        if "and" in genre:
            index_of_and = genre.index("and")
            genre[index_of_and] = ""
        genre = '_'.join(genre)
        print(genre)
    else:
        genre = ''.join(genre)
    
    url = "https://www.rottentomatoes.com/top/bestofrt/top_100_" + genre + "_movies/"
    print(url)
    response = requests.get(url)

    soup = BeautifulSoup(response.text, 'html.parser')
    movie_table = soup.find('table', class_='table')

    # 'tr' is the tag that holds the data for each movie
    tr = movie_table.find_all('tr')

    movie_array = []
    for x in range(1, len(tr)):
        movie_parse = tr[x].a.text.split(' ')
        movie_array.append(parse_movie_strings(movie_parse))
    
    response_and_movie = generate_response(movie_array, intent, response_genre)
    if another_movie is not None:
        response = another_movie + response_and_movie[0]
    else:
        response = response_and_movie[0]
    session_attributes = {"previous_intent": "get_movie_response", "movie": response_and_movie[1], "genre": genre, "response_genre": response_genre}
    
    speech_output = response
    reprompt_text = "I said," + response
    should_end_session = False
    
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def yes_no(intent, session):
    card_title = "YesNo"
    
    if session['attributes']['previous_intent'] == "get_movie_response":
        movie = session['attributes']['movie']
        
        if intent['name'] == "AMAZON.YesIntent":
            another_movie = "Ok, I'll find another one for you... "
            return get_movie_response(session, intent, another_movie, session['attributes']['genre'], session['attributes']['response_genre'])
        elif intent['name'] == "AMAZON.NoIntent":
            speech_output = "Ok, do you want to hear a brief summary of its plot?"
            session_attributes = {"previous_intent": "YesNo", "movie": movie, "genre": session['attributes']['genre'], "response_genre": session['attributes']['response_genre'], "another_movie": "None"}
    elif session['attributes']['previous_intent'] == "Welcome":
        speech_output = "Sorry, I didn't catch that. What movie genre did you want?"
        session_attributes = {"previous_intent": "Welcome"}
    elif session['attributes']['previous_intent'] == "YesNo":
        if session['attributes']['another_movie'] == "None": # get description of plot
            
            if intent['name'] == "AMAZON.YesIntent":
                movie = session['attributes']['movie']
                url = "https://google.com/search?q=" + urllib.parse.quote_plus(movie) + "+plot"
                response = requests.get(url)
        
                soup = BeautifulSoup(response.text, 'html.parser')
                print(soup.prettify())
                big_box = soup.find('div', class_="hwc")
                box2 = soup.find('div', class_="BNeawe tAd8D AP7Wnd")
                
                if len(big_box.text) > len(box2.text):
                    speech_output = delete_actor_names(big_box.text)
                else:
                    speech_output = delete_actor_names(box2.text)
                speech_output += ". Do you want to hear about another movie?"
                session_attributes = {"previous_intent": "YesNo", "movie": movie, "genre": session['attributes']['genre'], "response_genre": session['attributes']['response_genre'], "another_movie": "NotNone"}

            elif intent['name'] == "AMAZON.NoIntent":
                speech_output = "Ok, do you want me to find you another movie?"
                random_num = random.randint(0, 2)
                if random_num == 1:
                    speech_output += " (By the way, you can change genres at any time simply by saying the genre you want!)"
                session_attributes = {"previous_intent": "YesNo", "genre": session['attributes']['genre'], "response_genre": session['attributes']['response_genre'], "another_movie": "NotNone"}

        else: # find another movie
            if intent['name'] == "AMAZON.YesIntent":
                another_movie = "Ok, I'll find another one for you... "
                return get_movie_response(session, intent, another_movie, session['attributes']['genre'], session['attributes']['response_genre'])
            elif intent['name'] == "AMAZON.NoIntent": #end the session
                speech_output = "Thank you for trying movie match maker. I hope I was able to match you up with a great movie. Goodbye!"
                reprompt_text = speech_output
                session_attributes = {}
                should_end_session = True
                return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))

    reprompt_text = speech_output
    should_end_session = False
    
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def get_welcome_response():
    
    session_attributes = {"previous_intent": "Welcome"}
    card_title = "Welcome"
    speech_output = "Welcome to movie match maker, where a robot rids you of the burden of picking a movie to watch! Just tell me what movie genre you're feeling and I'll find you a great match."
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "I don't know if you heard me, Welcome to movie match maker, where a robot rids you of the burden of picking a movie to watch! Just tell me what movie genre you're feeling and I'll find you a great match."
    should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for trying movie match maker! Goodbye."
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    pass

def on_launch(launch_request, session):
    # Dispatch to launch message
    return get_welcome_response()


def on_intent(intent_request, session):
    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to intent handlers
    if intent_name == "findmovie":
        return get_movie_response(session, intent)
    elif intent_name == "AMAZON.NoIntent" or intent_name == "AMAZON.YesIntent":
        return yes_no(intent, session)
    elif intent_name == "AMAZON.HelpIntent" or intent_name == "HelloWorldIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    return handle_session_end_request()
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):

    print("Incoming request...")

    if (event['session']['application']['applicationId'] !=
            "amzn1.ask.skill.bf4ec96b-fd36-4996-9a3b-eb4610d20f39"):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])
    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
            
