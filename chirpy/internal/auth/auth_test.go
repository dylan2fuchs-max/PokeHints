package auth

import (
	"testing"
	"time"

	"github.com/google/uuid"
)

func TestJWT(t *testing.T) {
	userID := uuid.New()
	secret := "my-super-secret-key"
	wrongSecret := "wrong-secret-key"

	// 1. Test successful token creation and validation
	token, err := MakeJWT(userID, secret, time.Hour)
	if err != nil {
		t.Fatalf("failed to make JWT: %v", err)
	}

	parsedID, err := ValidateJWT(token, secret)
	if err != nil {
		t.Fatalf("failed to validate JWT: %v", err)
	}

	if parsedID != userID {
		t.Errorf("expected parsed ID %v, got %v", userID, parsedID)
	}

	// 2. Test expired token rejection
	expiredToken, err := MakeJWT(userID, secret, -time.Hour)
	if err != nil {
		t.Fatalf("failed to make expired JWT: %v", err)
	}

	_, err = ValidateJWT(expiredToken, secret)
	if err == nil {
		t.Error("expected error for expired token, got nil")
	}

	// 3. Test wrong secret rejection
	_, err = ValidateJWT(token, wrongSecret)
	if err == nil {
		t.Error("expected error for wrong secret, got nil")
	}
}

func TestGetBearerToken(t *testing.T) {
	// 1. Test valid header
	headers := http.Header{}
	headers.Set("Authorization", "Bearer my-token-123")
	token, err := GetBearerToken(headers)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if token != "my-token-123" {
		t.Errorf("expected 'my-token-123', got '%s'", token)
	}

	// 2. Test missing header
	emptyHeaders := http.Header{}
	_, err = GetBearerToken(emptyHeaders)
	if err == nil {
		t.Error("expected error for missing authorization header, got nil")
	}

	// 3. Test malformed header
	badHeaders := http.Header{}
	badHeaders.Set("Authorization", "Basic my-token-123")
	_, err = GetBearerToken(badHeaders)
	if err == nil {
		t.Error("expected error for malformed authorization header, got nil")
	}
}

func TestGetAPIKey(t *testing.T) {
	// 1. Test valid header
	headers := http.Header{}
	headers.Set("Authorization", "ApiKey secret-polka-key-123")
	key, err := GetAPIKey(headers)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if key != "secret-polka-key-123" {
		t.Errorf("expected 'secret-polka-key-123', got '%s'", key)
	}

	// 2. Test missing header
	emptyHeaders := http.Header{}
	_, err = GetAPIKey(emptyHeaders)
	if err == nil {
		t.Error("expected error for missing authorization header, got nil")
	}

	// 3. Test malformed header
	badHeaders := http.Header{}
	badHeaders.Set("Authorization", "Bearer secret-polka-key-123")
	_, err = GetAPIKey(badHeaders)
	if err == nil {
		t.Error("expected error for malformed authorization header, got nil")
	}
}