package com.example.hello.dto;

public class LoginResponse {

    private final String token;
    private final String tokenType;
    private final String username;

    public LoginResponse(String token, String tokenType, String username) {
        this.token = token;
        this.tokenType = tokenType;
        this.username = username;
    }

    public String getToken() {
        return token;
    }

    public String getTokenType() {
        return tokenType;
    }

    public String getUsername() {
        return username;
    }
}
