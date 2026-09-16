package com.example.hello.controller;

import com.example.hello.dto.LoginRequest;
import com.example.hello.dto.LoginResponse;
import com.example.hello.exception.InvalidCredentialsException;
import com.example.hello.security.JwtService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class LoginController {

    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;

    public LoginController(AuthenticationManager authenticationManager, JwtService jwtService) {
        this.authenticationManager = authenticationManager;
        this.jwtService = jwtService;
    }

    /**
     * Username-password login. On success returns a JWT to be used as
     * "Authorization: Bearer <token>" on protected endpoints.
     */
    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        Authentication authentication;
        try {
            authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(
                            request.getUsername(), request.getPassword()));
        } catch (BadCredentialsException e) {
            // BadCredentialsException is an AuthenticationException: if it escapes the
            // controller it is intercepted by ExceptionTranslationFilter and turned into
            // the generic entry-point 401. Translate it here so the client gets a
            // login-specific message from the GlobalExceptionHandler.
            throw new InvalidCredentialsException();
        }
        String token = jwtService.generateToken(authentication.getName());
        return ResponseEntity.ok(new LoginResponse(token, "Bearer", authentication.getName()));
    }
}
