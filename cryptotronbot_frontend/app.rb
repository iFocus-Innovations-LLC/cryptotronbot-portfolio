Ruby


require 'sinatra'
require 'erb'
# require 'httparty' # If needed

# configure do
#   # For a real app, manage API base URL better
#   set :api_base_url, 'http://localhost:5000/api' # Your Python backend URL
# end

get '/' do
  erb :index
end

get '/login' do
  erb :login
end

get '/register' do
  # You'd have a registration ERB template similar to login
  erb :register # Assuming you create register.erb
end

get '/dashboard' do
  # In a real app, you might check for a session cookie set by Ruby after login,
  # but here we'll rely on JS to handle auth with the Python backend.
  erb :dashboard
end

# Example of how a server-side route could proxy to the backend
# (less common if JS is directly calling the Python API)
# get '/api_proxy/portfolio' do
#   # This would require auth handling within Ruby as well
#   # headers = { "Authorization" => "Bearer #{session[:jwt_token]}" } # If JWT stored in Ruby session
#   # response = HTTParty.get("#{settings.api_base_url}/portfolio", headers: headers)
#   # content_type :json
#   # response.body
#   "Proxying not fully implemented for this example"
# end
