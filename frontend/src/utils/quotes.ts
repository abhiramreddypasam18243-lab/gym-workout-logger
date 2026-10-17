export interface MotivationalQuote {
  id: string
  quote: string
  author: string
  category: 'strength' | 'discipline' | 'resilience' | 'mindset' | 'greatness'
  context?: string
}

export const MOTIVATIONAL_QUOTES: MotivationalQuote[] = [
  {
    id: 'arnold-1',
    quote: 'The resistance that you fight physically in the gym and the resistance that you fight in life can only build a strong character.',
    author: 'Arnold Schwarzenegger',
    category: 'strength',
    context: '7x Mr. Olympia',
  },
  {
    id: 'arnold-2',
    quote: 'Strength does not come from winning. Your struggles develop your strengths. When you go through hardships and decide not to surrender, that is strength.',
    author: 'Arnold Schwarzenegger',
    category: 'strength',
    context: 'Bodybuilding Legend',
  },
  {
    id: 'rollins-1',
    quote: 'The Iron is the best master-teacher that I have ever found. In the pursuit of strength, the Iron will never lie to you. Two hundred pounds will always be two hundred pounds.',
    author: 'Henry Rollins',
    category: 'strength',
    context: 'Musician & Writer',
  },
  {
    id: 'ali-1',
    quote: "I hated every minute of training, but I said, 'Don't quit. Suffer now and live the rest of your life as a champion.'",
    author: 'Muhammad Ali',
    category: 'greatness',
    context: 'Heavyweight World Champion',
  },
  {
    id: 'ali-2',
    quote: 'Champions are made from something they have deep inside them: a desire, a dream, a vision.',
    author: 'Muhammad Ali',
    category: 'mindset',
    context: 'Boxing Icon',
  },
  {
    id: 'kobe-1',
    quote: 'Dedication sees dreams come true. If you do not believe in yourself, no one will do it for you.',
    author: 'Kobe Bryant',
    category: 'discipline',
    context: '5x NBA Champion',
  },
  {
    id: 'kobe-2',
    quote: 'Great things come from hard work and perseverance. No excuses.',
    author: 'Kobe Bryant',
    category: 'discipline',
    context: 'Mamba Mentality',
  },
  {
    id: 'marcus-1',
    quote: 'The impediment to action advances action. What stands in the way becomes the way.',
    author: 'Marcus Aurelius',
    category: 'mindset',
    context: 'Stoic Philosopher & Emperor',
  },
  {
    id: 'seneca-1',
    quote: 'Difficulties strengthen the mind, as labor does the body.',
    author: 'Seneca',
    category: 'resilience',
    context: 'Stoic Philosopher',
  },
  {
    id: 'socrates-1',
    quote: 'No citizen has a right to be an amateur in the matter of physical training. What a disgrace it is to grow old without ever seeing the beauty and strength of which the body is capable.',
    author: 'Socrates',
    category: 'strength',
    context: 'Classical Greek Philosopher',
  },
  {
    id: 'bruce-1',
    quote: 'Do not pray for an easy life, pray for the strength to endure a difficult one.',
    author: 'Bruce Lee',
    category: 'resilience',
    context: 'Martial Arts Master',
  },
  {
    id: 'bruce-2',
    quote: 'I fear not the man who has practiced 10,000 kicks once, but I fear the man who has practiced one kick 10,000 times.',
    author: 'Bruce Lee',
    category: 'discipline',
    context: 'Martial Artist & Philosopher',
  },
  {
    id: 'serena-1',
    quote: 'I really think a champion is defined not by their wins but by how they can recover when they fall.',
    author: 'Serena Williams',
    category: 'resilience',
    context: '23x Grand Slam Champion',
  },
  {
    id: 'kipchoge-1',
    quote: 'Only the disciplined ones in life are free. If you are undisciplined, you are a slave to your moods and your passions.',
    author: 'Eliud Kipchoge',
    category: 'discipline',
    context: 'World Record Marathoner (Sub-2h)',
  },
  {
    id: 'goggins-1',
    quote: 'You are in danger of living a life so comfortable and soft, that you will die without ever realizing your true potential.',
    author: 'David Goggins',
    category: 'mindset',
    context: 'Ultramarathon Athlete & Navy SEAL',
  },
  {
    id: 'goggins-2',
    quote: 'We don’t rise to the level of our expectations, we fall to the level of our training.',
    author: 'David Goggins',
    category: 'discipline',
    context: 'Endurance Athlete',
  },
  {
    id: 'ronnie-1',
    quote: "Everybody wants to be a bodybuilder, but nobody wants to lift no heavy-ass weights. Do it!",
    author: 'Ronnie Coleman',
    category: 'strength',
    context: '8x Mr. Olympia',
  },
  {
    id: 'ronnie-2',
    quote: "Hard work and training. There's no secret formula. I lift heavy, work hard, and aim to be the best.",
    author: 'Ronnie Coleman',
    category: 'strength',
    context: 'Hall of Fame Bodybuilder',
  },
  {
    id: 'jordan-1',
    quote: "I've failed over and over and over again in my life. And that is why I succeed.",
    author: 'Michael Jordan',
    category: 'greatness',
    context: '6x NBA Champion',
  },
  {
    id: 'jordan-2',
    quote: 'Obstacles don’t have to stop you. If you run into a wall, don’t turn around and give up. Figure out how to climb it, go through it, or work around it.',
    author: 'Michael Jordan',
    category: 'resilience',
    context: 'Basketball Legend',
  },
  {
    id: 'epictetus-1',
    quote: 'First say to yourself what you would be; and then do what you have to do.',
    author: 'Epictetus',
    category: 'mindset',
    context: 'Stoic Philosopher',
  },
  {
    id: 'vince-1',
    quote: 'The price of success is hard work, dedication to the job at hand, and the determination that whether we win or lose, we have applied the best of ourselves.',
    author: 'Vince Lombardi',
    category: 'greatness',
    context: 'Championship Coach',
  },
  {
    id: 'usain-1',
    quote: 'I trained 4 years to run 9 seconds, and people give up when they don’t see results in 2 months.',
    author: 'Usain Bolt',
    category: 'discipline',
    context: '8x Olympic Gold Medalist',
  },
  {
    id: 'simone-1',
    quote: "I'd rather regret the risks that didn't work out than the chances I didn't take at all.",
    author: 'Simone Biles',
    category: 'mindset',
    context: 'Most Decorated Gymnast in History',
  },
  {
    id: 'nelson-1',
    quote: 'It always seems impossible until it is done.',
    author: 'Nelson Mandela',
    category: 'resilience',
    context: 'Statesman & Leader',
  },
  {
    id: 'steve-1',
    quote: 'The only way to do great work is to love what you do. Stay hungry, stay foolish.',
    author: 'Steve Jobs',
    category: 'greatness',
    context: 'Innovator',
  },
  {
    id: 'theodore-1',
    quote: 'Far and away the best prize that life has to offer is the chance to work hard at work worth doing.',
    author: 'Theodore Roosevelt',
    category: 'strength',
    context: '26th US President',
  },
  {
    id: 'churchill-1',
    quote: 'Success is not final, failure is not fatal: it is the courage to continue that counts.',
    author: 'Winston Churchill',
    category: 'resilience',
    context: 'Statesman',
  },
  {
    id: 'tom-1',
    quote: 'If you want to perform at your peak, you have to invest the discipline every single day.',
    author: 'Tom Brady',
    category: 'discipline',
    context: '7x Super Bowl Champion',
  },
  {
    id: 'cbum-1',
    quote: "You have to be willing to suffer for the things you want most. Greatness isn't given; it is taken by discipline.",
    author: 'Chris Bumstead',
    category: 'strength',
    context: '5x Classic Physique Champion',
  },
  {
    id: 'dorian-1',
    quote: 'Concentration and mental toughness are the margins of victory.',
    author: 'Dorian Yates',
    category: 'mindset',
    context: '6x Mr. Olympia',
  },
  {
    id: 'ct-1',
    quote: "It's not about being the best. It's about being better than you were yesterday.",
    author: 'CT Fletcher',
    category: 'strength',
    context: 'Powerlifter & Master Motivator',
  },
]

export function getRandomQuote(): MotivationalQuote {
  const index = Math.floor(Math.random() * MOTIVATIONAL_QUOTES.length)
  return MOTIVATIONAL_QUOTES[index]
}

export function getDailyQuote(): MotivationalQuote {
  // Deterministic daily quote based on UTC date
  const now = new Date()
  const dayOfYear = Math.floor((now.getTime() - new Date(now.getFullYear(), 0, 0).getTime()) / 1000 / 60 / 60 / 24)
  const index = dayOfYear % MOTIVATIONAL_QUOTES.length
  return MOTIVATIONAL_QUOTES[index]
}

export function getQuotesByCategory(category: MotivationalQuote['category']): MotivationalQuote[] {
  return MOTIVATIONAL_QUOTES.filter((q) => q.category === category)
}
